"""余烬铸造厂的可平铺 PBR 贴图：铁格栅、耐火砖、熔流与锻造纹章。

不使用外部图片；固定种子保证可复建。熔流只有橙 / 琥珀色，红色留给敌方预警。
"""

import numpy as np

from arenas import textures as T

TILE_M, BRICK_M, LAVA_M, EMBLEM_R = 12.0, 4.0, 4.0, 14.5


def _line(d, width, aa):
    return 1.0 - T.smoothstep(width - aa, width + aa, np.abs(d))


def make_floor(n=1024, seed=263):
    """两米铆接铁板内嵌长孔格栅：用高度差体现孔洞与磨亮的倒角。"""
    px = TILE_M / n
    u = (np.arange(n) + 0.5) / n * TILE_M
    X, Z = np.meshgrid(u, u)
    noise = T.fbm_periodic(n, seed, beta=1.8, kmin=3, kmax=85)
    grain = T.fbm_periodic(n, seed + 1, beta=0.8, kmin=35, kmax=210)
    a, b = X % 2.0, Z % 2.0
    edge = np.minimum.reduce([a, 2 - a, b, 2 - b])
    inset = T.smoothstep(0.19, 0.22, edge)
    # r2：约三成铁板换成无孔的花纹钢板（扁豆纹交错），打破整片打孔网的单调平铺。
    pi, pj = np.floor(X / 2.0).astype(int), np.floor(Z / 2.0).astype(int)
    tread = (T.rand01(pi, pj, seed + 7) < 0.30).astype(float)
    # 孔洞宽 0.11 m、长 0.29 m；外框与横肋保证格栅在游戏距离可辨。
    sx = np.abs((X % 0.25) - 0.125)
    sz = np.abs((Z % 0.40) - 0.20)
    holes = (1 - T.smoothstep(0.049, 0.064, sx)) * (1 - T.smoothstep(0.133, 0.151, sz)) * inset * (1 - tread)
    rim = T.blur_periodic(holes, 1.35) - holes
    # 花纹钢板：0.16 m 网格上交替 ±45° 的扁豆凸纹，只有高度和微弱亮边。
    ga, gb = X % 0.16 - 0.08, Z % 0.16 - 0.08
    flip = ((np.floor(X / 0.16) + np.floor(Z / 0.16)) % 2) * 2 - 1
    la, lb = (ga + flip * gb) * 0.7071, (ga - flip * gb) * 0.7071
    lentil = (1 - T.smoothstep(0.75, 1.0, np.hypot(la / 0.052, lb / 0.014))) * inset * tread
    seams = 1 - T.smoothstep(0.015, 0.037, edge)
    wear = T.smoothstep(0.43, 0.73, noise)
    col = np.array([0.36, 0.352, 0.338])[None, None, :] * (0.72 + 0.48 * noise)[..., None]
    col *= (1 - 0.10 * tread)[..., None]
    # 铁锈只用低饱和棕灰；不会被看成红色攻击提示。
    rust = T.smoothstep(0.61, 0.82, noise) * (1 - wear * 0.35)
    col = col * (1 - 0.36 * rust[..., None]) + np.array([0.058, 0.034, 0.018]) * rust[..., None]
    col *= (1 - 0.70 * holes - 0.68 * seams)[..., None]
    col += np.maximum(0, rim)[..., None] * 0.40
    # 每块板四角的铆钉：深底座、磨亮的头和十字压痕。
    rivet = np.zeros((n, n))
    socket = np.zeros((n, n))
    for ax in (0.115, 1.885):
        for bz in (0.115, 1.885):
            d = np.hypot(a - ax, b - bz)
            rivet = np.maximum(rivet, 1 - T.smoothstep(0.026, 0.039, d))
            socket = np.maximum(socket, 1 - T.smoothstep(0.04, 0.057, d))
    col *= (1 - 0.33 * socket)[..., None]
    col += rivet[..., None] * 0.09
    scratch = np.maximum(0, np.sin((X + 0.25 * Z) * np.pi * 16)) ** 28 * wear * 0.008
    col += scratch[..., None]
    col += lentil[..., None] * (0.035 + 0.05 * wear)[..., None]
    h = -0.048 * holes - 0.018 * seams + 0.012 * rivet + 0.004 * lentil + 0.002 * (grain - 0.5)
    rough = np.clip(0.52 + 0.19 * rust - 0.14 * wear + 0.23 * holes, 0.30, 0.92)
    # 氧化表面保留漫反射，裸露磨痕稍具金属感；不靠高基础色抵消黑金属。
    metal = np.clip(0.14 + 0.10 * wear - 0.15 * holes - 0.14 * rust, 0.04, 0.30)
    mr = np.stack([np.zeros_like(rough), rough, metal], axis=-1)
    mr = mr.reshape(n // 2, 2, n // 2, 2, 3).mean(axis=(1, 3))
    return dict(base=T.to_u8(col), normal=T.normal_from_height(h, px, 1.0), mr=T.to_u8(mr))


def make_brick(n=512, seed=269):
    """黑灰耐火砖，交错砖缝、烧蚀裂纹与细孔。"""
    u = (np.arange(n) + 0.5) / n * BRICK_M
    X, Z = np.meshgrid(u, u)
    row = np.floor(Z / 0.5).astype(int)
    xx = (X + (row % 2) * 0.5) % 1.0
    zz = Z % 0.5
    edge = np.minimum.reduce([xx, 1 - xx, zz, 0.5 - zz])
    mortar = 1 - T.smoothstep(0.008, 0.025, edge)
    no = T.fbm_periodic(n, seed, beta=1.3, kmin=4, kmax=80)
    cell = T.rand01(np.floor((X + (row % 2) * 0.5)).astype(int), row, seed)
    col = (0.40 + 0.09 * (cell - 0.5) + 0.10 * (no - 0.5))[..., None] * np.array([1.0, 0.92, 0.82])
    col *= (1 - 0.58 * mortar)[..., None]
    h = -0.021 * mortar + 0.007 * (no - 0.5)
    return dict(base=T.to_u8(col), normal=T.normal_from_height(h, BRICK_M / n, 1.0))


def make_lava(n=512, seed=271):
    """r2：熔流表面是一块块漂浮的黑色结壳，板缝连成网透出琥珀光；色相不进入警示红区域。
    连续的熔芯另由几何窄带（Arena Molten Seam）给出，这里只负责结壳与细缝。"""
    vo = T.voronoi_tile(n, 9, 0.85, seed)
    e = vo["e1"] * LAVA_M                                  # 到板缝的距离（米）
    fine = T.fbm_periodic(n, seed + 1, beta=1.4, kmin=8, kmax=80)
    cell = T.rand01(vo["cid"], 0, seed)
    gap = 1 - T.smoothstep(0.012, 0.030, e)               # 板缝本体
    halo = 1 - T.smoothstep(0.03, 0.11, e)                # 板缝两侧被烤热的结壳边
    coal = np.array([0.030, 0.023, 0.016])[None, None, :] * (0.6 + 0.6 * fine + 0.3 * cell)[..., None]
    ember = np.array([0.36, 0.17, 0.045])[None, None, :]
    amber = np.array([0.62, 0.40, 0.08])[None, None, :]
    col = coal + ember * (halo * (1 - gap) * 0.55)[..., None]
    col = col * (1 - gap[..., None]) + amber * gap[..., None]
    # 发光只取最窄的板缝中线，且部分板缝被冷却断开，覆盖率远低于 4% 上限。
    live = T.smoothstep(0.45, 0.68, fine)
    em = amber * ((1 - T.smoothstep(0.003, 0.011, e)) * live * 0.95)[..., None]
    h = T.smoothstep(0.0, 0.06, e) * 0.022 + (fine - 0.5) * 0.004 + (cell - 0.5) * 0.004
    return dict(base=T.to_u8(col), normal=T.normal_from_height(h, LAVA_M / n, 0.9), emissive=T.to_u8(em))


def make_emblem(n=1024, seed=277):
    """锻造工会地面徽记：齿轮外缘、铁砧与锤，低对比黄铜嵌线。"""
    u = (np.arange(n) + 0.5) / n * 2 * EMBLEM_R - EMBLEM_R
    X, Z = np.meshgrid(u, u)
    r, th = np.hypot(X, Z), np.arctan2(Z, X)
    aa = 2 * EMBLEM_R / n * 1.25
    noise = T.fbm_periodic(n, seed, beta=1.6, kmin=3, kmax=80)
    col = (0.42 + 0.08 * (noise - 0.5))[..., None] * np.array([1.0, 0.98, 0.95])
    ink = np.maximum(_line(r - 12.6, 0.070, aa), _line(r - 10.95, 0.045, aa))
    tooth = _line(r - (12.95 + 0.42 * (np.cos(th * 40) > 0)), 0.07, aa)
    ink = np.maximum(ink, tooth)
    # 图案是锻造工具而不是魔法光圈：带双肩与锥形角的铁砧。
    top = (np.abs(Z + 0.90) < 0.16) & (X > -3.7) & (X < 3.6)
    base = (np.abs(Z - 2.4) < 0.13) & (np.abs(X) < 2.0)
    shank = _line(np.abs(X) - (1.20 + 0.45 * np.clip((Z - 0.1) / 2.2, 0, 1)), 0.095, aa) * (Z > -0.7) * (Z < 2.5)
    horn = _line(Z + 0.9 + 0.45 * (X - 3.6), 0.095, aa) * (X > 3.5) * (X < 5.0)
    ink = np.maximum.reduce([ink, top.astype(float), base.astype(float), shank, horn])
    # 铁锤柄与锤头略倾斜，与底部铆接标线区分。
    A, B = X * 0.86 + Z * 0.51, -X * 0.51 + Z * 0.86
    handle = _line(A + 1.0, 0.08, aa) * (B > -5.0) * (B < -1.2)
    head = (np.abs(A + 1.0) < 1.15) & (np.abs(B + 5.1) < 0.35)
    ink = np.maximum.reduce([ink, handle, head.astype(float)])
    lines = ink.copy()                                     # 发光只取线条，不含铆钉
    # 环内铆钉与刻度（不发光）。
    for k in range(12):
        a = k * np.pi / 6
        dot = 1 - T.smoothstep(0.09, 0.16, np.hypot(X - 11.8 * np.cos(a), Z - 11.8 * np.sin(a)))
        ink = np.maximum(ink, dot)
    brass = np.array([0.60, 0.47, 0.29])[None, None, :]
    col = col * (1 - ink[..., None]) + brass * (0.82 + 0.22 * noise)[..., None] * ink[..., None]
    h = ink * 0.012 + (noise - 0.5) * 0.0015
    rough = 0.56 - ink * 0.17
    metal = 0.38 + ink * 0.25
    mr = np.stack([np.zeros_like(rough), rough, metal], axis=-1).reshape(n // 2, 2, n // 2, 2, 3).mean(axis=(1, 3))
    # r2：嵌线像刚浇铸的黄铜，留一点余热；只取线条中线，发光覆盖控制在 4% 以下。
    core_line = T.smoothstep(0.55, 0.9, T.blur_periodic(lines, 1.2)) * lines
    # 锤头 / 砧面这类实心块只让边缘发热，内部压暗，避免整块亮成一张贴纸。
    core_line *= 1 - 0.75 * T.smoothstep(0.85, 0.98, T.blur_periodic(lines, 5.0))
    # 外圈齿轮是主要轮廓；中央铁砧 / 锤只留一半余热，混战时不抢角色和预警。
    core_line *= np.where(r < 9.5, 0.5, 1.0)
    em = np.array([0.95, 0.56, 0.16])[None, None, :] * (core_line * (0.55 + 0.45 * noise))[..., None]
    return dict(base=T.to_u8(col), normal=T.normal_from_height(h, 2 * EMBLEM_R / n, 1.0), mr=T.to_u8(mr),
                emissive=T.to_u8(em))
