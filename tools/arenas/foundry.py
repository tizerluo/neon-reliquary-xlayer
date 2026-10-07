"""余烬铸造厂（区域 2）：铆接铁格栅、熔流沟槽与废弃锻造车间。

高炉 / 龙门架 / 传送带全部位于战斗边界外；中心十八米只有平面纹章。
沿用既有场地接口与预算，不改变共享网格工具或角色 / 战斗渲染。
"""

import math
import os
import random

import numpy as np

from arenas import common as C
from arenas import foundry_tex as FT
from arenas import textures as T
from arenas.common import MatSpec, Mesh, Part

ID, TITLE, MOOD = "foundry", "Ember Foundry", "#d8986d"
EMBLEM_CENTER = (0.0, 0.0)
FLOOR = "Arena Floor Iron Grating"
EMBLEM = "Arena Emblem Forge Guild"
BRICK = "Arena Refractory Brick"
STEEL = "Arena Forged Steel"
TRIM = "Arena Oxidized Copper"
SOOT = "Arena Furnace Soot"
SLAG = "Arena Cold Slag"
LAVA = "Arena Molten Amber"
MOUTH = "Arena Furnace Amber"
SHAFT = "Arena Shaft Heat"
# r2：地面热缝的纯色发光材质（名字含 seam → glow.js 给 0.25 辉光权重）
SEAM = "Arena Molten Seam"
PARTS = os.environ.get("ARENA_PARTS", "floor,bounds,props,lights").split(",")


def make_specs(texdir):
    """所有贴图都由固定种子的配方生成；迭代几何时可显式使用本地缓存。"""
    recipes = dict(floor=FT.make_floor, emblem=FT.make_emblem, brick=FT.make_brick, lava=FT.make_lava)
    keys = dict(floor=("base", "normal", "mr"), emblem=("base", "normal", "mr", "emissive"), brick=("base", "normal"), lava=("base", "normal", "emissive"))
    cached = os.environ.get("ARENA_TEXCACHE") == "1"
    for name, fn in recipes.items():
        if not (cached and all((texdir / f"{name}_{k}.png").exists() for k in keys[name])):
            for key, arr in fn().items():
                T.write_png(texdir / f"{name}_{key}.png", arr)
    def tex(name):
        return {k: texdir / f"{name}_{k}.png" for k in keys[name]}
    return {
        FLOOR: MatSpec(FLOOR, tex=tex("floor"), uv="floor", uv_scale=FT.TILE_M, normal_strength=1.0),
        EMBLEM: MatSpec(EMBLEM, tex=tex("emblem"), strength=0.30, uv="floor", uv_scale=2 * FT.EMBLEM_R, uv_offset=(0.5, 0.5)),
        BRICK: MatSpec(BRICK, tex=tex("brick"), rough=0.88, uv="box", uv_scale=FT.BRICK_M),
        STEEL: MatSpec(STEEL, base="#525558", metal=0.72, rough=0.48),
        TRIM: MatSpec(TRIM, base="#71543a", metal=0.68, rough=0.58),
        SOOT: MatSpec(SOOT, base="#111419", rough=0.98),
        SLAG: MatSpec(SLAG, base="#34302b", rough=0.93),
        LAVA: MatSpec(LAVA, tex=tex("lava"), uv="floor", uv_scale=FT.LAVA_M, strength=0.70, rough=0.72),
        SEAM: MatSpec(SEAM, base="#1a1208", emit="#f0973a", strength=0.8, rough=0.9),
        MOUTH: MatSpec(MOUTH, base="#211c13", emit="#e99b35", strength=1.05, rough=0.9),
        # 光柱只在外部高炉口附近；强度按 alpha 预乘，不扫过中心战场。
        SHAFT: MatSpec(SHAFT, base="#000000", emit="#e4a751", strength=0.20, alpha=0.15, vcolor_alpha=True, rough=1.0),
    }


def _beam(m, mat, a, b, width=0.18, depth=None):
    """任意方向的矩形钢梁；顶点在源端烘好，GLB 无旋转节点。"""
    a, b = np.array(a, float), np.array(b, float)
    d = b - a
    length = float(np.linalg.norm(d))
    if length < 1e-6:
        return
    with m.at((a + b) / 2, math.atan2(d[0], d[2]), -math.asin(d[1] / length)):
        m.box(mat, (width, depth or width, length), anchor="center")


def _anvil(m, x, z, yaw=0.0, scale=1.0):
    """宽肩铁砧：收腰砧座、平砧面、圆锥角与方形尾。"""
    with m.at((x, 0, z), yaw, scale=scale):
        m.box(BRICK, (2.3, 0.8, 1.6), chamfer=0.09)
        m.stack_rect(STEEL, 0.97, 0.65, [(0, 0.8), (0.18, 1.12), (0.40, 1.85), (0.10, 2.14), (0.0, 2.42)])
        m.box(STEEL, (2.8, 0.42, 1.25), pos=(0, 2.25, 0), chamfer=0.07)
        # 方锥砧角朝东；四点的锥体有凸体绕序保障。
        V = [(1.30, 2.33, -0.43), (1.30, 2.33, 0.43), (1.30, 2.66, 0.43), (1.30, 2.66, -0.43), (2.75, 2.51, 0)]
        m.solid(STEEL, V, [[0, 1, 2, 3], [0, 4, 1], [1, 4, 2], [2, 4, 3], [3, 4, 0]])
        m.box(TRIM, (0.48, 0.045, 0.5), pos=(-0.75, 2.675, 0), chamfer=0.0)
        for xx in (-0.9, 0.9):
            for zz in (-0.59, 0.59):
                with m.at((xx, 0.82, zz)):
                    m.lathe(TRIM, [(0.09, 0), (0.07, 0.08)], 6, smooth=False, cap_bottom=False)


def _furnace(m, x, z, height, seed):
    """中空拱口高炉，能看见炉膛与炉栅；背墙在开口后，不用发光方块冒充炉门。"""
    rng = random.Random(seed)
    with m.at((x, 0, z)):
        # 前侧开口半径 3.1 m、拱肩 4.2 m；左 / 右炉体包住拱口。
        for sx in (-4.3, 4.3):
            m.box(BRICK, (2.1, height - 3.2, 5.0), pos=(sx, 0, -1.8), chamfer=0.16)
            m.box(STEEL, (0.30, height - 4.0, 0.32), pos=(sx, 0.6, 0.91))
        m.box(BRICK, (7.0, 1.1, 4.7), pos=(0, 7.8, -1.85), chamfer=0.12)
        m.box(BRICK, (6.5, height - 9.0, 4.1), pos=(0, 9.0, -2.05), chamfer=0.14)
        m.box(SOOT, (6.2, 6.8, 0.16), pos=(0, 0.25, -3.0))
        # 拱石是有厚度的独立楔块，导出时合并到同一个静态网格。
        for k in range(15):
            a0, a1 = math.pi * k / 15 + 0.007, math.pi * (k + 1) / 15 - 0.007
            V = [(r * math.cos(a), 4.2 + r * math.sin(a), zz)
                 for zz in (0.5, -0.8) for r in (3.1, 4.25) for a in (a0, a1)]
            m.solid(BRICK, V, [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]])
        m.box(BRICK, (7.3, 0.4, 2.0), pos=(0, 0, 0.2), chamfer=0.06)
        # 炉床与不规则余烬藏在暗炉栅之后，冷炉渣打断连续发光面。
        m.box(MOUTH, (5.75, 0.14, 1.65), pos=(0, 0.40, -0.90), chamfer=0.02)
        for k in range(13):
            xx = -2.8 + k * 0.46
            h = rng.uniform(0.65, 2.1)
            m.box(MOUTH, (0.44, h, 0.35), pos=(xx, 0.45, -1.12), taper=0.30)
            m.box(STEEL, (0.085, 4.3, 0.16), pos=(xx, 0.38, -0.05))
            m.rock(SLAG, (0.30, 0.20, 0.35), (xx, 0.49, -0.28), seed=seed * 100 + k)
        for yy in (0.95, 2.8):
            m.box(STEEL, (6.1, 0.12, 0.18), pos=(0, yy, 0.06))
        # 排烟管与风口，保留三层：砌体 / 钢带 / 暖色炉口。
        with m.at((0, height - 1.3, -2.0)):
            m.lathe(BRICK, [(1.4, 0), (1.3, 0.6), (1.0, 2.2), (1.0, 3.2)], 12, smooth=False)
            for yy in (0.4, 2.7):
                m.lathe(STEEL, [(1.38, yy), (1.38, yy + 0.18)], 12, smooth=False)
        for side in (-1, 1):
            _beam(m, STEEL, (side * 4.7, 4.3, -1.0), (side * 6.0, 4.3, -1.0), 0.42)
            m.box(TRIM, (0.24, 2.1, 0.32), pos=(side * 5.6, 1.3, -0.7))
            m.box(STEEL, (1.6, 0.16, 1.4), pos=(side * 4.5, 0.4, 1.0))


def _conveyor(m, x, z, yaw, length=16.0, seed=1):
    """矿料传送带：双轨、滚轴、鳞片输送板、支脚和炉渣负载。"""
    rng = random.Random(seed)
    with m.at((x, 0, z), yaw):
        for sx in (-1.1, 1.1):
            m.box(STEEL, (0.16, 0.36, length), pos=(sx, 0.85, 0), chamfer=0.025)
        for k in range(int(length / 0.8)):
            zz = -length / 2 + (k + 0.5) * 0.8
            m.box(STEEL, (2.0, 0.08, 0.72), pos=(0, 1.0, zz), tint=(0.55 + 0.3 * rng.random(),) * 3)
            for sx in (-1.13, 1.13):
                with m.at((sx, 1.08, zz), roll=math.pi / 2):
                    m.lathe(TRIM, [(0.12, 0), (0.12, 0.09)], 8, cap_bottom=False)
            if k % 3 == 0:
                m.rock(SLAG, (0.46, 0.38, 0.4), (rng.uniform(-0.5, 0.5), 1.12, zz), seed=seed * 100 + k)
        for zz in np.arange(-length / 2 + 1, length / 2, 3.2):
            for sx in (-0.9, 0.9):
                m.box(STEEL, (0.18, 1.0, 0.18), pos=(sx, 0, float(zz)))
            _beam(m, TRIM, (-0.9, 0.2, zz), (0.9, 0.85, zz), 0.08)


def _gantry(m, x, z, height=12.0, span=12.0):
    """铆接龙门吊：斜撑、双梁、钢索、悬挂锻锤，全部在边界外。"""
    for sx in (-span / 2, span / 2):
        m.box(BRICK, (1.6, 0.75, 1.8), pos=(x + sx, 0, z))
        for dz in (-0.55, 0.55):
            m.box(STEEL, (0.32, height, 0.26), pos=(x + sx, 0.65, z + dz))
        for yy in np.arange(1.0, height - 1, 2.0):
            _beam(m, TRIM, (x + sx, yy, z - 0.55), (x + sx, yy + 1.8, z + 0.55), 0.10)
    for dz in (-0.60, 0.60):
        m.box(STEEL, (span + 1.2, 0.35, 0.28), pos=(x, height + 0.35, z + dz))
    for xx in np.arange(-span / 2, span / 2 - 1.2, 1.5):
        _beam(m, TRIM, (x + xx, height + 0.55, z - 0.55), (x + xx + 1.45, height + 0.55, z + 0.55), 0.09)
    m.box(STEEL, (2.3, 0.8, 2.0), pos=(x + 1.5, height - 0.35, z))
    for xx in (-0.4, 0.4):
        _beam(m, STEEL, (x + 1.5 + xx, height, z), (x + 1.5 + xx, 5.4, z), 0.07)
    m.box(STEEL, (2.6, 1.4, 1.7), pos=(x + 1.5, 4.0, z), chamfer=0.10)
    m.box(TRIM, (2.64, 0.20, 1.75), pos=(x + 1.5, 4.2, z))


# 熔流沟槽中线：(起点, 终点)，地面坐标 (x, z)。热缝与暖色地面都以到沟槽的距离为参照。
CHANNELS = [((x, z0), (x, z1)) for x in (-26.0, 26.0) for z0, z1 in ((-37.0, -8.0), (8.0, 35.0))] + \
           [((x0, -30.0), (x1, -30.0)) for x0, x1 in ((-38.0, -8.0), (8.0, 38.0))]


def _channel_dist(x, z):
    """点（可为数组）到最近熔流沟槽中线的距离（米）。"""
    x, z = np.asarray(x, float), np.asarray(z, float)
    best = np.full(np.broadcast(x, z).shape, 1e9)
    for (ax, az), (bx, bz) in CHANNELS:
        dx, dz = bx - ax, bz - az
        t = np.clip(((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz), 0, 1)
        best = np.minimum(best, np.hypot(x - ax - t * dx, z - az - t * dz))
    return best


def _molten_vein(m, a, b, seed, half=0.10):
    """沟槽里连续的熔芯：沿中线轻微蜿蜒、宽度起伏的发光窄带，替代 r1 断续的蚯蚓纹。
    用炉膛材质（辉光权重低）：本身够亮，但不会在俯视下晕成一道激光。"""
    rng = np.random.default_rng(seed)
    a, b = np.array(a, float), np.array(b, float)
    length = float(np.linalg.norm(b - a))
    k = max(int(length / 0.6), 2)
    t = np.linspace(0, 1, k + 1)
    side = np.array([-(b - a)[1], (b - a)[0]]) / length
    ph = rng.random(3) * math.tau
    wob = 0.05 * np.sin(t * length * 0.9 + ph[0]) + 0.03 * np.sin(t * length * 2.3 + ph[1])
    pts = [tuple(a + (b - a) * ti + side * w) for ti, w in zip(t, wob)]
    wid = half * (1.0 + 0.55 * np.sin(t * length * 1.7 + ph[2]) * np.sin(t * length * 0.43))
    wid[0] = wid[-1] = 0.02
    m.strip_xz(MOUTH, pts, list(np.clip(wid, 0.03, 0.18)), y=0.014)


def _heat_seams(m, seed=431):
    """地面热缝：熔流的热量顺着两米铁板接缝向外渗出的短琥珀线。
    大部分从沟槽旁出发、背离沟槽走 1–3 格，少量零散 L 形短缝；越往中心越稀，纹章内不放。
    只是贴地窄带，不挡路；每段都收尖，避免读成横贯全场的激光线。"""
    rng = np.random.default_rng(seed)
    lim_x, lim_z, clear_r = 44.0 + 3.0, 40.0 + 3.0, FT.EMBLEM_R + 1.0
    dirs = [(2, 0), (-2, 0), (0, 2), (0, -2)]
    ok = lambda x, z: math.hypot(x, z) >= clear_r and abs(x) <= lim_x and abs(z) <= lim_z

    def emit(pts, w0):
        dense = []
        for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
            dense += [(ax + (bx - ax) * f, az + (bz - az) * f) for f in (0, 0.25, 0.5, 0.75)]
        dense.append(pts[-1])
        n = len(dense)
        # 起点（贴沟槽一端）最宽，末端收成发丝。
        wid = [w0 * (1 - i / (n - 1)) ** 0.7 + 0.006 for i in range(n)]
        m.strip_xz(SEAM, dense, wid, y=0.009)

    count = 0
    # 一、从沟槽两侧的接缝节点出发，先背离沟槽，再随机拐弯。
    starts = []
    for (ax, az), (bx, bz) in CHANNELS:
        if ax == bx:
            starts += [((ax + side, float(z)), (int(side), 0)) for side in (-2, 2)
                       for z in np.arange(math.ceil(min(az, bz) / 2) * 2, max(az, bz) + 0.1, 2.0)]
        else:
            starts += [((float(x), az + side), (0, int(side))) for side in (-2, 2)
                       for x in np.arange(math.ceil(min(ax, bx) / 2) * 2, max(ax, bx) + 0.1, 2.0)]
    for (x0, z0), d0 in starts:
        if rng.random() > 0.30 or not ok(x0, z0):
            continue
        pts, (dx, dz) = [(x0 - d0[0] * 0.38, z0 - d0[1] * 0.38), (x0, z0)], d0   # 从沟槽钢沿处接出
        for _ in range(int(rng.integers(0, 3))):
            if rng.random() < 0.45:
                dx, dz = [(ddx, ddz) for ddx, ddz in dirs if (ddx, ddz) not in ((-dx, -dz), (dx, dz))][rng.integers(2)]
            nxt = (pts[-1][0] + dx, pts[-1][1] + dz)
            if not ok(*nxt) or float(_channel_dist(*nxt)) < 1.5:
                break
            pts.append(nxt)
        emit(pts, 0.085)
        count += 1
    # 二、零散的 L 形短缝：概率随离沟槽距离衰减，中心附近几乎没有。
    tries = 0
    while tries < 3000 and count < 110:
        tries += 1
        x0, z0 = 2.0 * rng.integers(-23, 24), 2.0 * rng.integers(-21, 22)
        d = float(_channel_dist(x0, z0))
        if not ok(x0, z0) or d < 2.5 or rng.random() > 0.05 + 0.5 * math.exp(-d / 6.0):
            continue
        a = dirs[rng.integers(4)]
        b = [q for q in dirs if q not in (a, (-a[0], -a[1]))][rng.integers(2)]
        p1 = (x0 + a[0], z0 + a[1])
        pts = [(x0, z0), p1] + ([(p1[0] + b[0], p1[1] + b[1])] if rng.random() < 0.5 else [])
        if all(ok(*q) for q in pts):
            emit(pts, 0.05)
            count += 1
    return count


def build_floor():
    m = Mesh(283)
    P = C.floor_grid(m, FLOOR, cell=2.0)
    # 宏观烧蚀 / 油污降低机械平铺感，颜色仍以中性的暗铁灰为主。
    macro = C.vnoise(P, 0.052, 283)
    tint = 0.63 + macro * 0.35
    # r2：沟槽两侧五米内的铁板被烤出青铜 / 麦秆色回火痕，中心仍是冷铁灰。
    heat = np.exp(-_channel_dist(P[:, 0], P[:, 2]) / 4.0)
    warm = np.stack([1 + 0.16 * heat, 1 - 0.02 * heat, 1 - 0.22 * heat], axis=-1)
    m.C[-1][:, :3] *= np.stack([tint, tint * 0.98, tint * 0.96], axis=-1) * warm
    C.disc(m, EMBLEM, FT.EMBLEM_R, seg=112, rings=8, y=0.012, tint=(0.80, 0.78, 0.74))
    # 纹章外缘一圈铸铁护环，把中心徽记从格栅里框出来（高 5 cm，可走过）。
    with m.at((0, 0.012, 0)):
        m.lathe(STEEL, [(FT.EMBLEM_R - 0.02, -0.01), (FT.EMBLEM_R + 0.36, -0.01), (FT.EMBLEM_R + 0.36, 0.03),
                        (FT.EMBLEM_R + 0.16, 0.05), (FT.EMBLEM_R - 0.02, 0.05), (FT.EMBLEM_R - 0.02, -0.01)], 112,
                smooth=False, cap_bottom=False, cap_top=False)
    # 沟槽是地表贴合件，外覆桥板；只占外围，中心清爽且不影响行走。
    for i, ((x0, z0), (x1, z1)) in enumerate(CHANNELS):
        vertical = x0 == x1
        wide = 1.0 if vertical else 0.86
        m.strip_xz(SOOT, [(x0, z0), (x1, z1)], [wide, wide], y=0.007)
        m.strip_xz(LAVA, [(x0, z0), (x1, z1)], [wide * 0.62, wide * 0.62], y=0.011)
        _molten_vein(m, (x0, z0), (x1, z1), 440 + i, half=0.06 if vertical else 0.07)
        for off in (-wide * 0.42, wide * 0.42):
            ox, oz = (off, 0.0) if vertical else (0.0, off)
            m.strip_xz(STEEL, [(x0 + ox, z0 + oz), (x1 + ox, z1 + oz)], [0.11, 0.11], y=0.026)
        if vertical:
            for zz in np.arange(z0 + 1.2, z1, 5.8):
                # 鳞片桥板横跨沟槽，地面高度仍远低于 0.12 m 上限。
                m.box(STEEL, (1.26, 0.045, 0.38), pos=(x0, 0.027, float(zz)), chamfer=0.012)
    print(f"FLOOR heat seams {_heat_seams(m)}")
    return [Part("FLOOR_FORGE", "ARENA_FLOOR", m)]


def build_bounds():
    rail, north, sides, south = Mesh(293), Mesh(307), Mesh(311), Mesh(313)
    # 低矮防护沿贴在战斗边界外：铁底座、分段栏杆与黄铜卡箍。
    for sign in (-1, 1):
        for z in np.arange(-38, 40, 4.0):
            rail.box(BRICK, (1.10, 0.48, 3.9), pos=(sign * 44.70, 0, float(z)))
            rail.box(STEEL, (0.13, 0.16, 3.9), pos=(sign * 44.42, 1.05, float(z)))
            rail.box(STEEL, (0.16, 1.28, 0.16), pos=(sign * 44.42, 0, float(z)))
            rail.box(TRIM, (0.18, 0.08, 0.18), pos=(sign * 44.42, 1.10, float(z)))
        for x in np.arange(-42, 44, 4.0):
            rail.box(BRICK, (3.9, 0.48, 1.1), pos=(float(x), 0, sign * 40.70))
            rail.box(STEEL, (3.9, 0.16, 0.13), pos=(float(x), 1.05, sign * 40.42))
            rail.box(STEEL, (0.16, 1.28, 0.16), pos=(float(x), 0, sign * 40.42))
    # 北排：两座不同高炉 + 中间锻锤，后排铁肋墙与烟管形成工业天际线。
    _furnace(north, -20, -47.6, 14.0, 317)
    _furnace(north, 22, -49.0, 16.0, 331)
    _gantry(north, 1, -46.2, 11.0, 13.0)
    _conveyor(north, -8, -44.0, math.pi / 2, 10, 337)
    _anvil(north, 1.7, -42.3, 0.0, 0.82)
    for x in (-37, -8, 9, 38):
        with north.at((x, 0, -53)):
            north.lathe(BRICK, [(1.15, 0), (1.0, 0.8), (0.80, 11.5), (0.85, 12.0), (0.68, 17.0)], 10, smooth=False)
            for yy in (2.0, 7.0, 11.5, 15.0):
                north.lathe(STEEL, [(0.90, yy), (0.90, yy + 0.25)], 10, smooth=False)
    for x in np.arange(-40, 42, 6.0):
        north.box(BRICK, (5.9, 4.3 + 0.9 * math.sin(x), 1.0), pos=(float(x), 0, -57))
        north.box(STEEL, (0.23, 8.5, 0.34), pos=(float(x), 0, -56.5))
    # 东西：传送带和铁砧足够靠近边缘，南侧只留低矮炉渣 / 轨道。
    for sign in (-1, 1):
        _conveyor(sides, sign * 49.0, -10.0, 0, 28.0, 347 + sign)
        _gantry(sides, sign * 53.0, -29.0, 9.0, 9.0)
        for zz in (10.0, 24.0):
            _anvil(sides, sign * 49.0, zz, sign * 0.35, 1.15)
            sides.box(BRICK, (3.4, 1.0, 3.0), pos=(sign * 53.5, 0, zz + 1), chamfer=0.10)
        for zz in (-24, 3, 32):
            C.rubble_heap(sides, SLAG, sign * 53.5, zz, 2.6, 30, 1.35, 359 + zz + sign)
    _conveyor(south, 0, 45.0, math.pi / 2, 30, 367)
    for x in (-34, -19, 19, 35):
        C.rubble_heap(south, SLAG, x, 44.5, 2.8, 28, 1.10, 373 + x, ymax=1.8)
        south.box(STEEL, (4.0, 0.30, 0.36), pos=(x, 0.2, 46.1), yaw=0.10)
    for mesh in (rail, north, sides, south):
        mesh.paint(C.weathered_paint(seed=389, dirt_h=3.0, dirt=0.60, moss=False))
    C.bake_ao([rail, north, sides, south], skip_mats=(MOUTH,), samples=10, dist=3.8, strength=0.48, seed=397)
    return [Part("BOUNDS_SAFETY_RAIL", "ARENA_BOUNDS", rail), Part("BOUNDS_BLAST_FURNACES", "ARENA_BOUNDS", north),
            Part("BOUNDS_CONVEYOR_WORKS", "ARENA_BOUNDS", sides), Part("BOUNDS_SOUTH_SCRAP", "ARENA_BOUNDS", south)]


def build_props():
    m, rng = Mesh(401), random.Random(401)
    pts = C.poisson(rng, 65, lambda x, z: math.hypot(x, z) > 20.0 and abs(x) < 41.5 and abs(z) < 37.5,
                    4.8, (-41, 41, -37, 37))
    for i, (x, z) in enumerate(pts):
        s = rng.uniform(0.18, 0.43)
        m.rock(SLAG, (s, s * 0.48, s * 0.73), (x, 0, z), seed=409 + i, yaw=rng.random() * math.tau, detail=0)
        if i % 3 == 0:
            with m.at((x + 0.35, 0, z + 0.25), rng.random() * math.tau):
                m.box(STEEL, (0.9, 0.09, 0.28), pos=(0, 0.04, 0), chamfer=0.02, tint=(0.4, 0.4, 0.4))
                m.box(TRIM, (0.22, 0.08, 0.35), pos=(0.15, 0.14, 0), tint=(0.45, 0.45, 0.45))
    C.bake_ao([m], samples=8, dist=0.8, strength=0.45, seed=419)
    return [Part("PROPS_FORGE_SCRAP", "ARENA_PROPS", m)]


def build_lights():
    """两片低强度炉口暖光，仅在外侧；实际动态火星 / 热浪仍是后续可选项。"""
    parts = []
    for i, x in enumerate((-20.0, 22.0)):
        m = Mesh(421 + i)
        # 顶点透明度从炉口向外衰减，光片没有纯红和横跨战场的明亮带。
        rows, cols = 6, 4
        P, A, F = [], [], []
        for j in range(rows + 1):
            t = j / rows
            for k in range(cols + 1):
                u = k / cols * 2 - 1
                P.append((x + u * (1.8 + t * 2.4), 2.9 * (1 - t), -46.6 + t * 4.0))
                A.append((1 - abs(u)) * (1 - t) ** 2)
        for j in range(rows):
            for k in range(cols):
                a = j * (cols + 1) + k
                F.append([a, a + 1, a + cols + 2, a + cols + 1])
        m.add(np.array(P), F, SHAFT, alpha=np.array(A))
        parts.append(Part(f"LIGHT_SHAFT_FURNACE_{i}", "ARENA_LIGHTS", m))
    return parts


def build():
    parts = []
    for name, fn in (("floor", build_floor), ("bounds", build_bounds), ("props", build_props), ("lights", build_lights)):
        if name in PARTS:
            parts += fn()
    return parts
