"""六套圣物飞剑 · 游戏版配方。

每个配方 build_<id>(m) 往 Mesh m 里加几何，返回材质列表（Mesh 里的材质下标即列表下标）。
统一坐标：剑尖 +X（≈0.85）、剑首 ≈ -0.55、剑身平躺在 XY 平面（厚度沿 Z）、原点在护手中心。
材质一律三个以内：0 主体 / 1 贵金属或滚边 / 2 小面积自发光。
自发光材质命名用 Seam / Vein / Hem / Rune（游戏选择性辉光权重 0.25–0.3、强度 ×1.1），
刻意不含 core / glow / eye / heart / slit，也不用 inlay（强度 ×1.4），几百把同屏不糊。
"""

import math

from mathutils import Vector

from .geo import make_material

TAU = math.tau

# 主题色（与 src/renderer.js 的 NRCOLORS 一致，自发光直接用，不改色相）
COLORS = {
    "aurelian": "#7cece1",
    "mordred": "#ffac64",
    "volt": "#86b9ff",
    "nyx": "#c39bff",
    "seraph": "#ff8ea8",
    "isolde": "#9beefb",
}

# 面数预算（硬性规格）
BUDGET = {"aurelian": 300, "mordred": 300, "volt": 300, "nyx": 200, "seraph": 300, "isolde": 300}

# 审图取景：detail 相机看向的点 / 距离
DETAIL = {
    "aurelian": ((0.0, 0, 0), 0.75),
    "mordred": ((0.15, 0, 0), 1.2),
    "volt": ((0.10, 0.05, 0), 1.2),
    "nyx": ((-0.30, 0, 0), 0.75),
    "seraph": ((0.20, 0, 0), 1.0),
    "isolde": ((0.30, 0, 0), 1.0),
}


def lerp(a, b, t):
    return a + (b - a) * t


def yz_rect(x, hy, hz, cy=0.0):
    return [(x, cy - hy, -hz), (x, cy + hy, -hz), (x, cy + hy, hz), (x, cy - hy, hz)]


def xz_rect(y, cx, hx, hz):
    return [(cx - hx, y, -hz), (cx + hx, y, -hz), (cx + hx, y, hz), (cx - hx, y, hz)]


# =====================================================================
# 奥瑞利安 · 细长以太剑：窄长剑身 + 黄铜十字护手 + 剑脊一条青光槽
# =====================================================================
def build_aurelian(m):
    steel = make_material("Aurelian Blade Steel", "#b9d6d8", metal=0.85, rough=0.28)
    brass = make_material("Aurelian Blade Brass", "#c9a35a", metal=0.9, rough=0.32)
    seam = make_material("Aurelian Blade Seam", "#2a6f69", metal=0.2, rough=0.4,
                         emit=COLORS["aurelian"], strength=2.2)
    STEEL, BRASS, SEAM = 0, 1, 2

    # 剑身：六边截面（中间一条平顶 = 光槽），逐段收窄，尖端收到一点
    xs = [0.02, 0.22, 0.42, 0.60, 0.74]
    hw = [0.050, 0.050, 0.044, 0.034, 0.020]
    th = [0.011, 0.011, 0.010, 0.008, 0.005]
    gw = [0.014, 0.014, 0.012, 0.010, 0.006]
    rings = [m.vs([(x, -w, 0), (x, -g, t), (x, g, t), (x, w, 0), (x, g, -t), (x, -g, -t)])
             for x, w, t, g in zip(xs, hw, th, gw)]
    # 边：0 左刃面 / 1 上光槽 / 2 右刃面 / 3 右下刃面 / 4 下光槽 / 5 左下刃面
    m.loft(rings, [STEEL, SEAM, STEEL, STEEL, SEAM, STEEL])
    tip = m.v((0.85, 0, 0))
    m.fan(rings[-1], tip, STEEL)
    m.cap(rings[0], STEEL, m.pt((0.2, 0, 0)))

    # 剑身根部的黄铜护颈
    collar = [m.vs(yz_rect(0.015, 0.058, 0.016)), m.vs(yz_rect(0.060, 0.054, 0.0145))]
    m.loft(collar, BRASS)
    m.cap(collar[1], BRASS, m.pt((0.03, 0, 0)))  # 护颈比剑身略宽、略高，包住根部

    # 黄铜十字护手：沿 Y 的放样，两端向前掠起成燕尾
    g_st = [(-0.14, 0.040, 0.011, 0.009), (-0.07, 0.008, 0.021, 0.016), (0.0, 0.0, 0.032, 0.022),
            (0.07, 0.008, 0.021, 0.016), (0.14, 0.040, 0.011, 0.009)]
    g_rings = [m.vs(xz_rect(y, cx, hx, hz)) for y, cx, hx, hz in g_st]
    m.loft(g_rings, BRASS)
    for sgn, ring in ((-1, g_rings[0]), (1, g_rings[-1])):
        m.fan(ring, m.v((0.075, sgn * 0.175, 0)), BRASS)

    # 握柄 + 剑首：六边车削，剑首收成钻形
    prof = [(-0.02, 0.020), (-0.16, 0.027), (-0.30, 0.020), (-0.40, 0.042)]
    h_rings = [m.vs(m.polygon_yz(x, r)) for x, r in prof]
    m.loft(h_rings, BRASS)
    m.fan(h_rings[-1], m.v((-0.55, 0, 0)), BRASS)
    return [steel, brass, seam]


# =====================================================================
# 莫德雷德 · 熔炉巨刃：宽背斩刃（单刃、厚背、铆钉凸点），刃口烧红
# =====================================================================
def build_mordred(m):
    steel = make_material("Mordred Blade Steel", "#5c4a40", metal=0.8, rough=0.45)
    bronze = make_material("Mordred Blade Bronze", "#b07a3e", metal=0.9, rough=0.35)
    hem = make_material("Mordred Blade Hem", "#7a2d12", metal=0.2, rough=0.5,
                        emit=COLORS["mordred"], strength=2.3)
    STEEL, BRONZE, HEM = 0, 1, 2

    xs = [0.02, 0.20, 0.38, 0.54, 0.68, 0.78]
    ys = [0.095, 0.095, 0.095, 0.095, 0.090, 0.072]      # 刀背（厚）
    ye = [-0.110, -0.125, -0.135, -0.130, -0.108, -0.060]  # 刃口（外凸的腹部）
    th = [0.032, 0.034, 0.034, 0.032, 0.026, 0.018]
    rings = []
    for x, s, e, t in zip(xs, ys, ye, th):
        bw = min(0.055, 0.28 * (s - e))                  # 烧红的刃口斜面宽度
        rings.append(m.vs([(x, s, t), (x, e + bw, 0.011), (x, e, 0), (x, e + bw, -0.011), (x, s, -t)]))
    # 边：0 上刃面(钢) / 1 上刃口(红) / 2 下刃口(红) / 3 下刃面(钢) / 4 刀背
    m.loft(rings, [STEEL, HEM, HEM, STEEL, STEEL])
    m.fan(rings[-1], m.v((0.85, 0.030, 0)), [STEEL, HEM, HEM, STEEL, STEEL])
    m.cap(rings[0], STEEL, m.pt((0.2, 0, 0)))

    def top_z(x, y):
        """刀背侧上表面的高度（用于把铆钉贴在面上）。"""
        i = max(k for k in range(len(xs)) if xs[k] <= x)
        j = min(i + 1, len(xs) - 1)
        u = 0 if j == i else (x - xs[i]) / (xs[j] - xs[i])
        s, e, t = lerp(ys[i], ys[j], u), lerp(ye[i], ye[j], u), lerp(th[i], th[j], u)
        bw = min(0.055, 0.28 * (s - e))
        v = (y - s) / ((e + bw) - s)                     # 0 刀背 … 1 刃口斜面起点
        return lerp(t, 0.011, max(0.0, min(1.0, v)))

    # 刀背铆钉：六边小圆丘（青铜）
    for rx in (0.12, 0.27, 0.42, 0.57):
        ry = 0.060
        z0 = top_z(rx, ry)
        base = [(rx + 0.017 * math.cos(k * TAU / 6), ry + 0.017 * math.sin(k * TAU / 6), z0 - 0.003)
                for k in range(6)]
        m.pyramid(BRONZE, base, (rx, ry, z0 + 0.015))

    # 刃面上三道斜向的烧红裂口（贴面窄片）
    for sx in (0.22, 0.34, 0.46):
        a, b = (sx, -0.015), (sx + 0.045, -0.072)
        w = 0.0045
        quad = []
        for (px, py), side in ((a, -1), (a, 1), (b, 1), (b, -1)):
            quad.append((px + side * w * 0.7, py + side * w * 0.7, top_z(px, py) + 0.002))
        ids = m.vs(quad)
        m.face(HEM, ids, m.pt((sx, -0.04, -0.05)))

    # 护手：青铜短横档（尖两端）
    gst = [(-0.115, 0.0, 0.012, 0.018), (0.0, 0.0, 0.030, 0.030), (0.115, 0.0, 0.012, 0.018)]
    g_rings = [m.vs(xz_rect(y, cx, hx, hz)) for y, cx, hx, hz in gst]
    m.loft(g_rings, BRONZE)
    m.fan(g_rings[0], m.v((0.0, -0.145, 0)), BRONZE)
    m.fan(g_rings[-1], m.v((0.0, 0.145, 0)), BRONZE)

    # 握柄（钢）+ 圆饼剑首 + 尾刺（青铜）
    prof = [(-0.03, 0.026), (-0.17, 0.030), (-0.30, 0.024)]
    h_rings = [m.vs(m.polygon_yz(x, r)) for x, r in prof]
    m.loft(h_rings, STEEL)
    pom = [m.vs(m.polygon_yz(-0.325, 0.056)), m.vs(m.polygon_yz(-0.39, 0.056)), m.vs(m.polygon_yz(-0.41, 0.030))]
    m.loft([h_rings[-1], pom[0]], BRONZE)
    m.loft(pom, BRONZE)
    m.fan(pom[-1], m.v((-0.55, 0, 0)), BRONZE)
    return [steel, bronze, hem]


# =====================================================================
# 沃尔特 · 电弧獠牙：弯曲獠牙形短刃，之字形电纹凹槽（发光）+ 锯齿倒钩
# =====================================================================
def build_volt(m):
    steel = make_material("Volt Blade Steel", "#2c4468", metal=0.85, rough=0.30)
    silver = make_material("Volt Blade Silver", "#c5d4e6", metal=0.9, rough=0.25)
    vein = make_material("Volt Blade Vein", "#2b5aa0", metal=0.2, rough=0.4,
                         emit=COLORS["volt"], strength=2.4)
    STEEL, SILVER, VEIN = 0, 1, 2

    X0, LEN, CURL = -0.18, 1.03, 0.17

    def center(s):
        return X0 + LEN * s, CURL * s * s

    def tangent(s):
        dx, dy = LEN, 2 * CURL * s
        n = math.hypot(dx, dy)
        return dx / n, dy / n

    def width(s):
        return 0.108 * (1 - s ** 1.5) ** 0.9

    ss = [0.0, 0.14, 0.28, 0.42, 0.56, 0.70, 0.84]
    rings, edge_in = [], []
    for k, s in enumerate(ss):
        cx, cy = center(s)
        tx, ty = tangent(s)
        nx, ny = -ty, tx                                   # 指向凹侧（+Y 侧）
        hw = width(s)
        t = 0.020 * (1 - s) + 0.006
        g = min(0.020, 0.30 * hw)
        off = (1 if k % 2 else -1) * min(0.022, 0.30 * hw)  # 之字形：光槽左右交替
        P = lambda d, z: (cx + nx * d, cy + ny * d, z)
        rings.append(m.vs([P(-hw, 0), P(off - g, t), P(off + g, t), P(hw, 0), P(off + g, -t), P(off - g, -t)]))
        edge_in.append(P(hw, 0))
    m.loft(rings, [STEEL, VEIN, STEEL, STEEL, VEIN, STEEL])
    m.fan(rings[-1], m.v((*center(1.0), 0)), STEEL)
    m.cap(rings[0], STEEL, m.pt((X0 + 0.1, 0.01, 0)))

    # 凹侧三枚倒钩：扁三角棱柱，尖端朝前外
    for s in (0.30, 0.46, 0.62):
        cx, cy = center(s)
        tx, ty = tangent(s)
        nx, ny = -ty, tx
        hw = width(s)
        d0 = LEN * 0.075
        base_a = (cx - tx * d0 + nx * (hw - 0.012), cy - ty * d0 + ny * (hw - 0.012))
        base_b = (cx + tx * d0 * 0.6 + nx * (hw - 0.012), cy + ty * d0 * 0.6 + ny * (hw - 0.012))
        tip = (cx + tx * d0 * 1.55 + nx * (hw + 0.042), cy + ty * d0 * 1.55 + ny * (hw + 0.042))
        z = 0.006
        m.prism(STEEL, [(*base_a, z), (*base_b, z), (*tip, z)], [(*base_a, -z), (*base_b, -z), (*tip, -z)])

    # 护手：银色细横档
    gst = [(-0.13, -0.20, 0.007, 0.012), (0.0, -0.20, 0.020, 0.018), (0.13, -0.20, 0.007, 0.012)]
    g_rings = [m.vs(xz_rect(y, cx, hx, hz)) for y, cx, hx, hz in gst]
    m.loft(g_rings, SILVER)
    m.cap(g_rings[0], SILVER, m.pt((-0.20, 0, 0)))
    m.cap(g_rings[-1], SILVER, m.pt((-0.20, 0, 0)))

    # 握柄（钢）+ 剑首发光小八面体
    prof = [(-0.215, 0.022), (-0.33, 0.028), (-0.44, 0.022)]
    h_rings = [m.vs(m.polygon_yz(x, r)) for x, r in prof]
    m.loft(h_rings, STEEL)
    m.cap(h_rings[0], STEEL, m.pt((-0.3, 0, 0)))
    oct_ring = m.vs([(-0.50, 0.045, 0), (-0.50, 0, 0.045), (-0.50, -0.045, 0), (-0.50, 0, -0.045)])
    m.fan(oct_ring, m.v((-0.44, 0, 0)), VEIN, ref=m.pt((-0.50, 0, 0)))
    m.fan(oct_ring, m.v((-0.55, 0, 0)), VEIN, ref=m.pt((-0.50, 0, 0)))
    return [steel, silver, vein]


# =====================================================================
# 尼克斯 · 蜂群针刃：极细长针，菱形截面，尾部小环（≤200 面）
# =====================================================================
def build_nyx(m):
    steel = make_material("Nyx Needle Steel", "#6c56a8", metal=0.7, rough=0.34)
    plat = make_material("Nyx Needle Platinum", "#a396ba", metal=1.0, rough=0.28)
    rune = make_material("Nyx Needle Rune", "#6a4aa8", metal=0.2, rough=0.4,
                         emit=COLORS["nyx"], strength=1.7)
    STEEL, PLAT, RUNE = 0, 1, 2

    # 针身：扁菱形截面，上下各一条极窄的发光脊线（g 取半宽的 1/3），尾粗头细
    prof = [(-0.30, 0.020), (-0.20, 0.036), (0.00, 0.042), (0.25, 0.032), (0.55, 0.017)]
    rings = []
    for x, w in prof:
        h, g = 0.85 * w, 0.32 * w
        rings.append(m.vs([(x, -w, 0), (x, -g, h), (x, g, h), (x, w, 0), (x, g, -h), (x, -g, -h)]))
    m.loft(rings, [STEEL, RUNE, STEEL, STEEL, RUNE, STEEL])
    m.fan(rings[-1], m.v((0.85, 0, 0)), STEEL)
    m.cap(rings[0], STEEL, m.pt((-0.1, 0, 0)))

    # 铂金菱形护颈
    mid = m.vs([(-0.285, 0.046, 0), (-0.285, 0, 0.046), (-0.285, -0.046, 0), (-0.285, 0, -0.046)])
    m.fan(mid, m.v((-0.19, 0, 0)), PLAT, ref=m.pt((-0.285, 0, 0)))
    m.fan(mid, m.v((-0.38, 0, 0)), PLAT, ref=m.pt((-0.285, 0, 0)))

    # 尾部小环：十段、菱形截面的扁环（发光）
    cx, R, r, N = -0.455, 0.065, 0.014, 10
    ring_rings = []
    for k in range(N):
        a = TAU * k / N
        ux, uy = math.cos(a), math.sin(a)
        ring_rings.append(m.vs([(cx + ux * (R + r), uy * (R + r), 0), (cx + ux * R, uy * R, r),
                                (cx + ux * (R - r), uy * (R - r), 0), (cx + ux * R, uy * R, -r)]))
    ring_rings.append(ring_rings[0])
    for k in range(N):
        a, b = ring_rings[k], ring_rings[k + 1]
        mid_a = (k + 0.5) / N * TAU                      # 截面中心在环的中线上：用它当内部参考点
        ref = m.pt((cx + math.cos(mid_a) * R, math.sin(mid_a) * R, 0))
        for e in range(4):
            m.face(RUNE, [a[e], a[(e + 1) % 4], b[(e + 1) % 4], b[e]], ref)

    # 两片后掠尾翼（铂金，扁三角棱柱）
    for sgn in (-1, 1):
        z = 0.005
        tri = [(-0.17, sgn * 0.018), (-0.31, sgn * 0.015), (-0.345, sgn * 0.088)]
        m.prism(PLAT, [(*p, z) for p in tri], [(*p, -z) for p in tri])
    return [steel, plat, rune]


# =====================================================================
# 塞拉芙 · 赤红光环刃：花瓣 / 羽形刃片，玫瑰金边，脊上一线光
# =====================================================================
def _petal_main(m, BODY, GOLD, VEIN):
    xs = [-0.02, 0.12, 0.30, 0.48, 0.64, 0.76]
    hw = [0.035, 0.105, 0.135, 0.112, 0.066, 0.030]
    th = [0.020, 0.024, 0.026, 0.022, 0.015, 0.008]
    rings = []
    for x, w, t in zip(xs, hw, th):
        rb = min(0.030, 0.55 * w)
        g = min(0.010, 0.30 * w)
        rim = w - rb
        rings.append(m.vs([(x, -g, t), (x, g, t), (x, rim, 0.007), (x, w, 0), (x, rim, -0.007),
                           (x, g, -t), (x, -g, -t), (x, -rim, -0.007), (x, -w, 0), (x, -rim, 0.007)]))
    #       0 上脊光 1 右上面  2 右上滚边 3 右下滚边 4 右下面 5 下脊光 6 左下面 7 左下滚边 8 左上滚边 9 左上面
    mats = [VEIN, BODY, GOLD, GOLD, BODY, VEIN, BODY, GOLD, GOLD, BODY]
    m.loft(rings, mats)
    m.fan(rings[-1], m.v((0.85, 0, 0)), mats)
    m.cap(rings[0], GOLD, m.pt((0.2, 0, 0)))


def build_seraph(m):
    lacquer = make_material("Seraph Blade Lacquer", "#9c1f45", metal=0.35, rough=0.30)
    gold = make_material("Seraph Blade Rosegold", "#e0a08c", metal=1.0, rough=0.27)
    vein = make_material("Seraph Blade Vein", "#b0405f", metal=0.2, rough=0.4,
                         emit=COLORS["seraph"], strength=2.0)
    BODY, GOLD, VEIN = 0, 1, 2
    _petal_main(m, BODY, GOLD, VEIN)

    # 根部两枚小花瓣（玫瑰金），向前外侧张开
    for sgn in (-1, 1):
        with m.place(origin=(0.03, sgn * 0.030, 0), yaw=sgn * math.radians(20)):
            st = [(0.0, 0.032), (0.14, 0.060), (0.28, 0.044)]
            rings = [m.vs([(x, -w, 0), (x, 0, 0.014), (x, w, 0), (x, 0, -0.014)]) for x, w in st]
            m.loft(rings, GOLD)
            m.fan(rings[-1], m.v((0.37, 0, 0)), GOLD)
            m.cap(rings[0], GOLD, m.pt((0.1, 0, 0)))

    # 玫瑰金细柄 + 圆润剑首
    prof = [(-0.02, 0.016), (-0.20, 0.022), (-0.30, 0.044), (-0.40, 0.022)]
    h_rings = [m.vs(m.polygon_yz(x, r)) for x, r in prof]
    m.loft(h_rings, GOLD)
    m.fan(h_rings[-1], m.v((-0.53, 0, 0)), GOLD)
    return [lacquer, gold, vein]


# =====================================================================
# 伊索尔德 · 霜华冰魄：多面冰晶刃（锯折外廓），内部浅光，边缘银白高光
# =====================================================================
def build_isolde(m):
    ice = make_material("Isolde Blade Ice Crystal", "#a8e8f4", metal=0.0, rough=0.12, spec=1.0)
    silver = make_material("Isolde Blade Edge Silver", "#f2fbff", metal=1.0, rough=0.18)
    seam = make_material("Isolde Blade Seam", "#6fc4d6", metal=0.0, rough=0.3,
                         emit=COLORS["isolde"], strength=1.2)
    ICE, EDGE, SEAM = 0, 1, 2

    # 左右半宽独立 → 外廓像冰晶一级一级地凸出
    xs = [0.02, 0.14, 0.30, 0.46, 0.62, 0.74]
    hl = [0.045, 0.115, 0.070, 0.105, 0.050, 0.030]
    hr = [0.045, 0.060, 0.115, 0.075, 0.085, 0.035]
    th = [0.022, 0.032, 0.036, 0.034, 0.026, 0.014]
    rings = []
    for x, wl, wr, t in zip(xs, hl, hr, th):
        c = 0.30 * (wr - wl)
        rbl, rbr = min(0.028, 0.55 * wl), min(0.028, 0.55 * wr)
        g = min(0.018, 0.30 * min(wl, wr))
        rings.append(m.vs([(x, c - g, t), (x, c + g, t), (x, wr - rbr, 0.008), (x, wr, 0), (x, wr - rbr, -0.008),
                           (x, c + g, -t), (x, c - g, -t), (x, -wl + rbl, -0.008), (x, -wl, 0), (x, -wl + rbl, 0.008)]))
    mats = [SEAM, ICE, EDGE, EDGE, ICE, SEAM, ICE, EDGE, EDGE, ICE]
    m.loft(rings, mats)
    m.fan(rings[-1], m.v((0.85, 0, 0)), mats)
    m.cap(rings[0], ICE, m.pt((0.2, 0, 0)))

    # 两枚侧生冰晶（左后右前，错开位置）
    for sgn, ox, ln in ((-1, 0.10, 0.30), (1, 0.30, 0.27)):
        with m.place(origin=(ox, sgn * 0.075, 0), yaw=sgn * math.radians(32)):
            st = [(0.0, 0.030), (0.12, 0.048)]
            rings2 = [m.vs([(x, -w, 0), (x, 0, 0.022), (x, w, 0), (x, 0, -0.022)]) for x, w in st]
            m.loft(rings2, ICE)
            m.fan(rings2[-1], m.v((ln, 0, 0)), ICE)
            m.cap(rings2[0], ICE, m.pt((0.06, 0, 0)))

    # 银色细柄 + 冰晶剑首（六棱双锥）
    prof = [(0.04, 0.020), (-0.28, 0.020), (-0.36, 0.050)]
    h_rings = [m.vs(m.polygon_yz(x, r)) for x, r in prof]
    m.loft(h_rings, lambda k, e: EDGE if k == 0 else ICE)
    m.fan(h_rings[-1], m.v((-0.55, 0, 0)), ICE)
    return [ice, silver, seam]


RECIPES = {
    "aurelian": build_aurelian,
    "mordred": build_mordred,
    "volt": build_volt,
    "nyx": build_nyx,
    "seraph": build_seraph,
    "isolde": build_isolde,
}
