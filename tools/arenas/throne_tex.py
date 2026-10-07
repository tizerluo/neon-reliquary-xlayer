"""零域王座的可平铺 PBR 大理石与空位王冠纹章（r2），固定种子、无外部图片。

r2 终审结论：r1 的石脉只有 1–2 像素宽，游戏机位下看不见；纹章只是一圈均匀的细紫线，像界面边框。
r2 改为：扭曲域噪声的粗石脉 + 每块石板不同的石色 / 纹理偏移；纹章用明暗拼石（八角星 / 深色星图底 /
铭文边框 / 实心铂金王冠）读出主题，发光只留细芯、节点与星点。
"""

import math

import numpy as np

from arenas import textures as T

TILE_M, STONE_M, EMBLEM_R = 24.0, 5.0, 14.0   # r2：地面周期 16 → 24 m，游戏机位下不再看出重复
# 纹章几何（米，八角形“边心距”度量）：铭文边框、八角星、中央虚空盘
FRIEZE_IN, FRIEZE_OUT = 12.35, 13.55
STAR_TIP, STAR_WAIST, CORE_R = 11.75, 6.55, 4.55


def _line(d, width, aa):
    return 1 - T.smoothstep(width - aa, width + aa, np.abs(d))


def _veins(n, seed):
    """经典大理石脉：沿对角方向的正弦带 + 低频扰动，脉络连续、有走向，不会像等高线那样绕成闭合小圈。
    第二组交叉细脉只在主脉附近出现。整数频率保证可平铺。返回 (主脉, 主脉晕, 细裂脉, 云纹)。"""
    turb = T.fbm_periodic(n, seed, beta=2.6, kmin=1, kmax=6)
    wig = T.fbm_periodic(n, seed + 5, beta=2.0, kmin=3, kmax=20)
    detail = T.fbm_periodic(n, seed + 3, beta=1.6, kmin=6, kmax=60)
    u = (np.arange(n) + 0.5) / n
    U, V = np.meshgrid(u, u)
    ph = 2 * np.pi * (U + 2 * V) + 0.55 * 2 * np.pi * (turb - 0.5) + 0.18 * np.pi * (wig - 0.5)
    s = np.sin(ph)
    main = np.exp(-((s / 0.06) ** 2))
    halo = np.exp(-((s / 0.30) ** 2))
    ph2 = 2 * np.pi * (3 * U - V) + 1.1 * np.pi * (wig - 0.5) + 2 * np.pi * (turb - 0.5)
    thin = np.exp(-((np.sin(ph2) / 0.025) ** 2)) * (0.25 + 0.75 * halo)
    return main, halo, thin, detail


def make_floor(n=1024, seed=503):
    """磨光虚空大理石：4 m 错缝大板，每块石板单独的石脉偏移与石色（约两成为深色“夜石”），沉降板缝。"""
    u = (np.arange(n) + 0.5) / n * TILE_M
    X, Z = np.meshgrid(u, u)
    row = np.floor(Z / 4).astype(int)
    col_i = np.floor((X + (row % 2) * 2) / 4).astype(int)
    a, b = (X + (row % 2) * 2) % 4, Z % 4
    edge = np.minimum.reduce([a, 4 - a, b, 4 - b])
    seam = 1 - T.smoothstep(0.022, 0.060, edge)
    bevel = 1 - T.smoothstep(0.06, 0.22, edge)
    # 每块石板取同一张石脉场的不同位置，相邻石板石脉自然断开，像真实的切板拼装。
    main, halo, thin, detail = _veins(n, seed)
    cols = TILE_M / 4
    ox = T.rand01(col_i % cols, row % cols, seed + 11)
    oz = T.rand01(col_i % cols, row % cols, seed + 13)
    flip = T.rand01(col_i % cols, row % cols, seed + 17) < 0.5
    px, pz = X / TILE_M, Z / TILE_M
    sx = np.where(flip, pz, px) + ox
    sz = np.where(flip, px, pz) + oz
    m_s = T.sample_periodic(main, sx, sz)
    h_s = T.sample_periodic(halo, sx, sz)
    t_s = T.sample_periodic(thin, sx, sz)
    d_s = T.sample_periodic(detail, sx, sz)
    kind = T.rand01(col_i % cols, row % cols, seed + 19)
    nero = kind < 0.22
    shade = np.where(nero, 0.250, 0.335 + 0.05 * (kind - 0.6)) + 0.045 * (d_s - 0.5)
    col = shade[..., None] * np.array([0.95, 0.96, 1.05])
    vein_col = np.where(nero[..., None], np.array([0.30, 0.29, 0.36]), np.array([0.21, 0.20, 0.26]))
    col += vein_col * (0.85 * m_s + 0.22 * h_s + 0.45 * t_s)[..., None]
    col *= (1 - 0.66 * seam - 0.10 * bevel)[..., None]
    h = -0.018 * seam - 0.002 * bevel + 0.0006 * m_s + 0.0004 * (d_s - 0.5)
    rough = np.clip(0.26 + 0.10 * d_s + 0.30 * seam - 0.06 * m_s + 0.05 * nero, 0.22, 0.70)
    metal = 0.05 * (1 - seam)
    mr = np.stack([np.zeros_like(rough), rough, metal], axis=-1)
    mr = mr.reshape(n // 2, 2, n // 2, 2, 3).mean(axis=(1, 3))
    return dict(base=T.to_u8(col), normal=T.normal_from_height(h, TILE_M / n, 1), mr=T.to_u8(mr))


def make_stone(n=512, seed=509):
    """边界建筑的黑曜石色大理石；近看有天然石脉，远看保留大尺度轮廓。"""
    main, halo, thin, detail = _veins(n, seed)
    col = (0.26 + 0.05 * (detail - 0.5))[..., None] * np.array([0.92, 0.92, 1.04])
    col += np.array([0.12, 0.115, 0.15]) * (0.8 * main + 0.2 * halo + 0.4 * thin)[..., None]
    h = 0.0015 * main + 0.0008 * (detail - 0.5)
    return dict(base=T.to_u8(col), normal=T.normal_from_height(h, STONE_M / n, 1))


def _polygon(X, Z, pts):
    """多边形内部（射线法，向量化）。"""
    inside = np.zeros(X.shape, bool)
    for (ax, az), (bx, bz) in zip(pts, pts[1:] + pts[:1]):
        cross = ((az > Z) != (bz > Z)) & (X < (bx - ax) * (Z - az) / (bz - az + 1e-12) + ax)
        inside ^= cross
    return inside.astype(float)


def _segments(X, Z, pts, closed=True):
    """到折线的最近距离。"""
    d = np.full(X.shape, 1e9)
    seq = list(zip(pts, pts[1:] + pts[:1])) if closed else list(zip(pts[:-1], pts[1:]))
    for (ax, az), (bx, bz) in seq:
        dx, dz = bx - ax, bz - az
        t = np.clip(((X - ax) * dx + (Z - az) * dz) / (dx * dx + dz * dz), 0, 1)
        d = np.minimum(d, np.hypot(X - ax - t * dx, Z - az - t * dz))
    return d


def make_emblem(n=1024, seed=521):
    """空位王冠纹章：外圈深色铭文边框 → 浅色八角星拼石 + 深色星图底 → 中央虚空盘与实心铂金王冠。
    明暗拼石负责远看可读；发光只占细芯、八个节点、星点与王冠尖，中央整体压低，不读成范围预警。"""
    R = EMBLEM_R
    px = 2 * R / n
    u = (np.arange(n) + 0.5) * px - R
    X, Z = np.meshgrid(u, u)                      # X 向东，Z 向南（图像行向下 = 南）
    aa = 1.2 * px
    rng = np.random.default_rng(seed)
    r = np.hypot(X, Z)
    th = np.arctan2(Z, X)
    octa = np.maximum.reduce([np.abs(X), np.abs(Z), (np.abs(X) + np.abs(Z)) * 0.7071068])
    # 八角形局部坐标：转到最近一条边的法线方向，v = 沿边切向
    sec = np.round(th / (math.pi / 4))
    ca, sa = np.cos(-sec * math.pi / 4), np.sin(-sec * math.pi / 4)
    lx, lz = X * ca - Z * sa, X * sa + Z * ca
    # 十六分扇区坐标：八角星尖在 k·45°（边中点方向）
    fz = np.abs(lz)

    main, halo, thin, detail = _veins(n, seed)
    marble = 0.300 + 0.04 * (detail - 0.5) + 0.20 * main + 0.05 * halo + 0.10 * thin
    pale = 0.385 + 0.04 * (detail - 0.5) + 0.16 * main + 0.08 * thin
    nero = 0.150 + 0.025 * (detail - 0.5) + 0.06 * main
    voidg = 0.070 + 0.012 * (detail - 0.5)
    tone = marble.copy()
    metal_ink = np.zeros((n, n))                  # 铂金嵌条（金属、偏亮，不发光）
    em = np.zeros((n, n))                         # 自发光强度 0..1
    gem = np.zeros((n, n))                        # 节点 / 星点（最亮、最小）

    def inside(d):
        return T.smoothstep(-aa, aa, d)

    # 1) 铭文边框：深色夜石带 + 内外铂金线；铭文是一圈短刻符，每三格点亮一格的细芯
    band = inside(octa - FRIEZE_IN) * inside(FRIEZE_OUT - octa)
    tone = tone * (1 - band) + nero * band
    for d0, w in ((FRIEZE_IN, 0.075), (FRIEZE_OUT, 0.075), (FRIEZE_OUT + 0.22, 0.03)):
        metal_ink = np.maximum(metal_ink, _line(octa - d0, w, aa))
    mid = 0.5 * (FRIEZE_IN + FRIEZE_OUT)
    cell = 0.62
    ci = np.floor(lz / cell).astype(int)
    cu = (lz / cell - ci) - 0.5                   # 格内 -0.5..0.5
    cv = (lx - mid) / (FRIEZE_OUT - FRIEZE_IN)    # 带内 -0.5..0.5
    gk = (T.rand01(ci, sec.astype(int), seed) * 5).astype(int)
    lit = T.rand01(ci, sec.astype(int), seed + 3) < 0.30
    vert = np.abs(cu) < 0.08
    g = np.select(
        [gk == 0, gk == 1, gk == 2, gk == 3],
        [
            (np.abs(cu) < 0.07) & (np.abs(cv) < 0.30),                                # 竖笔
            (np.abs(np.abs(cu) - 0.18) < 0.07) & (np.abs(cv) < 0.24),                  # 双竖
            np.abs(np.abs(cv) * 0.9 - np.abs(cu) - 0.05) < 0.06,                      # 菱
            vert & (np.abs(cv) < 0.30) | (np.abs(cv + 0.22) < 0.06) & (np.abs(cu) < 0.22),  # 丁字
        ],
        np.hypot(cu, cv * 1.2) < 0.14,                                                 # 圆点
    )
    # 八个角点留空，放发光节点
    corner = np.abs(np.abs(lz) - mid * math.tan(math.pi / 8)) < 0.55
    glyph = g * band * (~corner)
    metal_ink = np.maximum(metal_ink, glyph * 0.85)
    em = np.maximum(em, glyph * lit * 0.55)
    for k in range(8):
        a = math.pi / 8 + k * math.pi / 4
        vr = mid / math.cos(math.pi / 8)
        cx, cz = vr * math.cos(a), vr * math.sin(a)
        dd = np.abs(X - cx) + np.abs(Z - cz)
        gem = np.maximum(gem, inside(0.24 - dd))
        metal_ink = np.maximum(metal_ink, _line(dd - 0.40, 0.04, aa))
    # 边框内侧一圈发光细芯：在八个角点处断开，不连成闭合亮圈
    core_ring = _line(octa - (FRIEZE_IN - 0.20), 0.024, aa) * (~corner)
    em = np.maximum(em, core_ring * 0.85)
    metal_ink = np.maximum(metal_ink, _line(octa - (FRIEZE_IN - 0.20), 0.06, aa))

    # 2) 八角星拼石：星尖指向八条边的中点；星内浅色石，星外深色星图底
    tip = np.array([STAR_TIP, 0.0])
    waist = np.array([STAR_WAIST * math.cos(math.pi / 8), STAR_WAIST * math.sin(math.pi / 8)])
    e = waist - tip
    nrm = np.array([-e[1], e[0]]) / np.linalg.norm(e)
    if nrm @ (-tip) < 0:
        nrm = -nrm
    sd = (lx - tip[0]) * nrm[0] + (fz - tip[1]) * nrm[1]     # >0 在星内
    star = inside(sd) * inside(FRIEZE_IN - 0.45 - octa)
    field = inside(FRIEZE_IN - 0.45 - octa) * (1 - star)
    # 罗盘玫瑰式的两面坡：每个星尖一半亮、一半暗，读出立体棱线而不是一整块平灰
    facet = np.where(lz > 0, 0.80, 1.0)
    tone = tone * (1 - star) + pale * facet * star
    tone = tone * (1 - field) + nero * field
    star_edge = _line(sd, 0.065, aa) * inside(FRIEZE_IN - 0.45 - octa) * inside(r - CORE_R - 0.3)
    metal_ink = np.maximum(metal_ink, star_edge)
    # 星尖到半腰的外段描一条细发光芯，内段只有铂金线（中央不亮）
    tip_part = T.smoothstep(STAR_WAIST + 0.6, STAR_TIP - 1.4, lx)
    em = np.maximum(em, _line(sd, 0.020, aa) * tip_part * 0.75 * inside(FRIEZE_IN - 0.5 - octa))
    # 星脊：每个星尖中线一条细铂金线
    spine = _line(fz, 0.035, aa) * star * inside(lx - CORE_R - 0.6)
    metal_ink = np.maximum(metal_ink, spine * 0.8)
    # 深色星图底：散落星点与几组星座连线（极细、低亮）
    pts = []
    tries = 0
    while len(pts) < 70 and tries < 4000:
        tries += 1
        x, z = rng.uniform(-R, R, 2)
        lo = math.hypot(x, z)
        if lo < CORE_R + 0.8 or lo > FRIEZE_IN:
            continue
        ix = int(np.clip((x + R) / px, 0, n - 1))
        iz = int(np.clip((z + R) / px, 0, n - 1))
        if field[iz, ix] < 0.99 or (star_edge[max(iz - 12, 0):iz + 12, max(ix - 12, 0):ix + 12].max() > 0.1):
            continue
        if any(math.hypot(x - a, z - b) < 0.9 for a, b, _ in pts):
            continue
        pts.append((x, z, rng.uniform(0.045, 0.11)))
    for x, z, s in pts:
        gem = np.maximum(gem, inside(s - np.hypot(X - x, Z - z)) * (0.55 + 4 * s))
    links = np.full((n, n), 1e9)
    for i, (x, z, _) in enumerate(pts):
        near = sorted(((math.hypot(x - a, z - b), j) for j, (a, b, _) in enumerate(pts) if j != i))[:1]
        for dist, j in near:
            if dist < 2.6 and i < j:
                links = np.minimum(links, _segments(X, Z, [(x, z), pts[j][:2]], closed=False))
    em = np.maximum(em, _line(links, 0.010, aa) * field * 0.30)

    # 3) 中央虚空盘：铂金双环 + 深色虚空玻璃 + 实心铂金王冠（空位，不发光）+ 中心“零点”细环
    ring = inside(CORE_R + 0.32 - r) * inside(r - CORE_R + 0.02)
    tone = tone * (1 - ring) + pale * ring
    metal_ink = np.maximum(metal_ink, _line(r - (CORE_R + 0.32), 0.05, aa))
    metal_ink = np.maximum(metal_ink, _line(r - CORE_R, 0.06, aa))
    disc = inside(CORE_R - r)
    tone = tone * (1 - disc) + voidg * disc
    # 刻度：外环 32 格短刻线
    tick = (np.abs(((th / math.tau * 32 + 0.5) % 1) - 0.5) * r * math.tau / 32 < 0.035) * ring
    metal_ink = np.maximum(metal_ink, tick * 0.9)
    crown = [(-2.7, -0.2), (-3.05, -2.55), (-1.55, -1.45), (0.0, -3.25), (1.55, -1.45),
             (3.05, -2.55), (2.7, -0.2)]
    crown = [(x, z - 0.15) for x, z in crown]
    cf = _polygon(X, Z, crown)
    band_c = _polygon(X, Z, [(-2.7, 0.05), (2.7, 0.05), (2.55, 0.62), (-2.55, 0.62)])
    crown_fill = np.maximum(cf, band_c)
    # 冠体镂空：冠带上一排小方孔，冠面中线一道竖槽，保留“空”的意思
    holes = (np.abs(((X / 0.72) + 0.5) % 1 - 0.5) < 0.18) & (np.abs(Z - 0.335) < 0.11) & (np.abs(X) < 2.2)
    crown_fill = crown_fill * (1 - holes)
    tone = tone * (1 - crown_fill) + 0.52 * crown_fill
    metal_ink = np.maximum(metal_ink, crown_fill)
    for x, z in [crown[1], crown[3], crown[5]]:
        dd = np.hypot(X - x, Z - (z - 0.38))
        gem = np.maximum(gem, inside(0.17 - dd) * 0.9)
    crown_line = _line(_segments(X, Z, crown + [(2.55, 0.62), (-2.55, 0.62)]), 0.02, aa)
    em = np.maximum(em, crown_line * 0.35 * (np.abs(X) > 0.4))
    # 王冠下方的“空座”：中空菱形与中心零点
    dia = np.abs(X) + np.abs(Z - 2.05) * 1.25
    metal_ink = np.maximum(metal_ink, _line(dia - 1.15, 0.05, aa))
    em = np.maximum(em, _line(dia - 1.15, 0.016, aa) * 0.5)
    gem = np.maximum(gem, inside(0.13 - np.hypot(X, Z - 2.05)) * 0.8)

    # 4) 合成：铂金嵌条覆盖在石色之上；整体偏冷的灰紫
    col = tone[..., None] * np.array([0.95, 0.96, 1.05])
    platinum = np.array([0.56, 0.55, 0.62])
    mi = np.clip(metal_ink, 0, 1)[..., None]
    col = col * (1 - mi) + platinum * mi
    h = 0.006 * metal_ink - 0.004 * band - 0.003 * disc + 0.0005 * (detail - 0.5)
    # 场地环境贴图是暗紫影棚：高金属度的嵌条会只反射黑色、在游戏里读成暗线。
    # 铂金嵌条只给 0.3 金属度，靠浅色基础色读出“亮金属线”；虚空盘稍光滑，带一点冷反光。
    rough = np.clip(0.34 + 0.07 * detail - 0.06 * metal_ink - 0.10 * disc, 0.16, 0.7)
    metal = np.clip(0.05 + 0.25 * metal_ink + 0.10 * disc, 0, 1)
    mr = (np.stack([np.zeros_like(rough), rough, metal], axis=-1)
          .reshape(n // 2, 2, n // 2, 2, 3).mean(axis=(1, 3)))
    # 发光：低饱和薰衣草细芯 + 冷白节点；中央（王冠 / 零点）压到 55%
    lav, white = np.array([0.66, 0.58, 0.92]), np.array([0.86, 0.86, 1.0])
    glow = lav * em[..., None] + white * np.clip(gem, 0, 1)[..., None]
    glow *= np.where(r < CORE_R + 0.4, 0.55, 1.0)[..., None]
    glow *= (0.80 + 0.20 * detail)[..., None]
    return dict(
        base=T.to_u8(col),
        normal=T.normal_from_height(h, px, 1),
        mr=T.to_u8(mr),
        emissive=T.to_u8(glow),
    )
