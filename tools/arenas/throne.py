"""零域王座（区域 3）：虚空大理石、灰紫嵌线、漂浮方尖碑与空位王座。

按余烬铸造厂 r2 的游戏机位标准制作：中心有主题微光，发光融入材质，
建筑位于可活动边界外，地图外围逐渐化为星空；不改已完成场地的配方。
"""

import math
import os
import random

import numpy as np

from arenas import common as C
from arenas import textures as T
from arenas import throne_tex as TT
from arenas.common import MatSpec, Mesh, Part

ID, TITLE, MOOD = "throne", "Null Throne", "#b89ccd"
EMBLEM_CENTER = (0, 0)
FLOOR = "Arena Floor Void Marble"
EMBLEM = "Arena Throne Inlay"
STONE = "Arena Obsidian Marble"
TRIM = "Arena Dusk Platinum"
BLACK = "Arena Void Glass"
CIRCUIT = "Arena Null Circuit"
SEAM = "Arena Obelisk Inlay"
STAR = "Arena Astral Dust"
SHAFT = "Arena Shaft Twilight"
RIFT = "Arena Null Rift Seam"   # 名字带 seam：选择性辉光按嵌缝权重给一圈淡紫光晕
PARTS = os.environ.get("ARENA_PARTS", "floor,bounds,props,lights").split(",")


def make_specs(texdir):
    recipes = dict(floor=TT.make_floor, stone=TT.make_stone, emblem=TT.make_emblem)
    keys = dict(
        floor=("base", "normal", "mr"),
        stone=("base", "normal"),
        emblem=("base", "normal", "mr", "emissive"),
    )
    cached = os.environ.get("ARENA_TEXCACHE") == "1"
    for name, fn in recipes.items():
        if not (
            cached and all((texdir / f"{name}_{k}.png").exists() for k in keys[name])
        ):
            for k, a in fn().items():
                T.write_png(texdir / f"{name}_{k}.png", a)

    def tex(name):
        return {k: texdir / f"{name}_{k}.png" for k in keys[name]}

    return {
        FLOOR: MatSpec(FLOOR, tex=tex("floor"), uv="floor", uv_scale=TT.TILE_M),
        EMBLEM: MatSpec(
            EMBLEM,
            tex=tex("emblem"),
            uv="floor",
            uv_scale=2 * TT.EMBLEM_R,
            uv_offset=(0.5, 0.5),
            strength=0.35,
        ),
        STONE: MatSpec(
            STONE,
            tex=tex("stone"),
            uv="box",
            uv_scale=TT.STONE_M,
            rough=0.33,
            metal=0.05,
        ),
        TRIM: MatSpec(TRIM, base="#676373", metal=0.76, rough=0.36),
        BLACK: MatSpec(BLACK, base="#181923", metal=0.30, rough=0.24),
        CIRCUIT: MatSpec(
            CIRCUIT, base="#272334", emit="#7d70b5", strength=0.40, rough=0.65
        ),
        SEAM: MatSpec(SEAM, base="#2d293a", emit="#9187b7", strength=0.30, rough=0.46),
        # r2：边缘向内蔓延的虚空裂隙，裂口下透出冷白星光（与铸造厂热缝同一角色）
        RIFT: MatSpec(RIFT, base="#0b0a12", emit="#9f94e2", strength=0.60, rough=0.9),
        STAR: MatSpec(STAR, base="#272c3d", emit="#a6b0ce", strength=0.24, rough=1),
        SHAFT: MatSpec(
            SHAFT,
            base="#000000",
            emit="#a09abb",
            strength=0.14,
            alpha=0.10,
            vcolor_alpha=True,
            rough=1,
        ),
    }


def _beam(m, mat, a, b, width=0.10, depth=None):
    a, b = np.array(a, float), np.array(b, float)
    d = b - a
    length = float(np.linalg.norm(d))
    if length < 1e-5:
        return
    with m.at((a + b) / 2, math.atan2(d[0], d[2]), -math.asin(d[1] / length)):
        m.box(mat, (width, depth or width, length), anchor="center")


_PATHS = []   # 已铺的电路折线，裂隙生成时避开


def _clear_of_paths(x, z, gap=0.9):
    for (ax, az), (bx, bz) in _PATHS:
        dx, dz = bx - ax, bz - az
        t = min(max(((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz + 1e-9), 0), 1)
        if math.hypot(x - ax - t * dx, z - az - t * dz) < gap:
            return False
    return True


def _path(m, pts, width=0.10, mat=CIRCUIT, y=0.011):
    """镶入石板的有限长度电路；留末端收尖和断口，不横贯整个战场。"""
    _PATHS.extend(zip(pts[:-1], pts[1:]))
    m.strip_xz(BLACK, pts, [width * 2.4] * len(pts), y=y - 0.003)
    widths = [width] * len(pts)
    widths[0] = widths[-1] = width * 0.30
    m.strip_xz(mat, pts, widths, y=y)


def _null_rifts(m, seed=613, count=34):
    """虚空裂隙：地图边缘正在“化为星空”，裂缝从边界向内蔓延 3–9 m，裂口透出冷白星光。
    折线带抖动、主干收尖、少量分叉；中心 18 m 内不放，外侧暗色裂唇给出深度。返回主干数。"""
    rng = np.random.default_rng(seed)
    lim_x, lim_z = 43.6, 39.6
    laid = []    # 其他裂缝家族的点：主干起点离它们 3 m 以上、行进中 0.8 m 以上，避免交叉成“X”

    def _near_rift(x, z, start):
        r = 3.0 if start else 0.8
        return any((x - a) ** 2 + (z - b) ** 2 < r * r for a, b in laid)

    def ok(x, z):
        return math.hypot(x, z) > 18.5 and abs(x) < lim_x and abs(z) < lim_z and _clear_of_paths(x, z)

    def crack(x, z, heading, length, w0, depth, family):
        pts = [(x, z)]
        h = heading
        walked = 0.0
        while walked < length:
            # 石材断裂：较长的直段 + 突然的折角，而不是闪电般连续抖动
            if rng.random() < 0.45:
                h = 0.55 * (h + rng.normal(0, 0.55)) + 0.45 * heading
            step = rng.uniform(0.5, 1.3)
            nx, nz = pts[-1][0] + step * math.cos(h), pts[-1][1] + step * math.sin(h)
            if not ok(nx, nz) or _near_rift(nx, nz, depth == 0 and len(pts) < 2):
                break
            # 每段再细分两次、侧向小抖动：断口是锯齿状的，不是一根直棍
            px, pz = pts[-1]
            for f in (0.33, 0.66):
                j = rng.normal(0, 0.07)
                pts.append((px + (nx - px) * f - j * math.sin(h), pz + (nz - pz) * f + j * math.cos(h)))
            pts.append((nx, nz))
            walked += step
        family.extend(pts)
        if len(pts) < 3:
            return 0
        k = len(pts)
        # 宽度沿裂缝起伏（崩口宽、挤压处窄），末端收成发丝
        wid = [(w0 * (1 - i / (k - 1)) ** 0.8) * rng.uniform(0.55, 1.25) + 0.010 for i in range(k)]
        wid[-1] = 0.008
        m.strip_xz(BLACK, pts, [w * 3.0 + 0.16 for w in wid], y=0.008)
        m.strip_xz(RIFT, pts, wid, y=0.010)
        if depth < 2:
            for i in range(2, k - 1):
                if rng.random() < 0.07:
                    side = rng.choice((-1, 1))
                    crack(*pts[i], h + side * rng.uniform(0.7, 1.2), length * rng.uniform(0.2, 0.35),
                          wid[i] * 0.75, depth + 1, family)
        return 1

    made, tries = 0, 0
    while made < count and tries < 600:
        tries += 1
        # 起点在战场外缘一圈（距边界 0–5 m），朝向场地中心并带随机偏角
        side = rng.integers(4)
        if side < 2:
            x = (1 if side else -1) * rng.uniform(lim_x - 5, lim_x - 0.2)
            z = rng.uniform(-lim_z + 1, lim_z - 1)
        else:
            z = (1 if side == 3 else -1) * rng.uniform(lim_z - 5, lim_z - 0.2)
            x = rng.uniform(-lim_x + 1, lim_x - 1)
        if not ok(x, z) or _near_rift(x, z, True):
            continue
        heading = math.atan2(-z, -x) + rng.normal(0, 0.45)
        family = []
        made += crack(x, z, heading, rng.uniform(3, 9), rng.uniform(0.10, 0.16), 0, family)
        laid.extend(family)
    return made


def build_floor():
    m = Mesh(541)
    P = C.floor_grid(m, FLOOR, cell=2)
    macro = C.vnoise(P, 0.040, 541)
    tint = 0.70 + 0.20 * macro
    # 活动范围内保留磨光石面，越过边界后十余米渐隐到与背景接近的虚空。
    edge = np.maximum(np.maximum(np.abs(P[:, 0]) - 46, np.abs(P[:, 2]) - 42), 0)
    fade = 1 - T.smoothstep(0, 13, edge)
    tint *= 0.012 + 0.988 * fade
    m.C[-1][:, :3] *= np.stack([tint * 0.96, tint * 0.97, tint], axis=-1)
    # r2：r1 的底盘 / 压边顶点在坐标轴上，和纹章八角形差 22.5°，游戏里看得出两层错位的八边形。
    # 现在底盘是边心距 14 m、边法线沿坐标轴的八边形，正好贴住 ±14 m 的纹章贴图。
    k8 = 1 / math.cos(math.pi / 8)
    with m.at((0, 0, 0), math.pi / 8):
        C.disc(m, EMBLEM, TT.EMBLEM_R * k8, seg=8, rings=8, y=0.013, tint=(0.80, 0.79, 0.84))
    # 八角金属压边仅 4 cm 高，压住纹章与地面石材的接缝；中央纹章仍是可行走的平面。
    pts = [
        (13.93 * k8 * math.cos(math.pi / 8 + math.tau * k / 8),
         13.93 * k8 * math.sin(math.pi / 8 + math.tau * k / 8))
        for k in range(9)
    ]
    m.strip_xz(TRIM, pts, [0.18] * len(pts), y=0.042)
    # 四向汇线由平台边缘收向纹章；双轨与方形接点区别于攻击线和移动拖尾。
    for k in range(4):
        a = k * math.pi / 2

        def turn(pts):
            return [
                (x * math.cos(a) - z * math.sin(a), x * math.sin(a) + z * math.cos(a))
                for x, z in pts
            ]

        for sign in (-1, 1):
            pts = [
                (sign * 4.5, 15.2),
                (sign * 4.5, 19.4),
                (sign * 8.1, 23),
                (sign * 8.1, 30.2),
            ]
            _path(m, turn(pts), 0.095)
            _path(
                m,
                turn(
                    [
                        (sign * 4.9, 15.6),
                        (sign * 4.9, 19.2),
                        (sign * 8.5, 22.8),
                        (sign * 8.5, 28.2),
                    ]
                ),
                0.042,
            )
            _path(
                m,
                turn([(sign * 8.1, 31.4), (sign * 8.1, 35.8), (sign * 11.8, 39.5)]),
                0.075,
            )
            for x, z in turn([(sign * 8.1, 30.7), (sign * 4.5, 18.5)]):
                with m.at((x, 0.012, z), a + math.pi / 4):
                    m.box(TRIM, (0.30, 0.018, 0.30), chamfer=0.018)
    # 角部稀疏的断续汇线，避免整片纹理变成高密度电路板。
    for sx in (-1, 1):
        for sz in (-1, 1):
            for i in range(3):
                x, z = 25 + i * 5, 20 + i * 3
                _path(
                    m,
                    [
                        (sx * x, sz * z),
                        (sx * (x + 2.8), sz * z),
                        (sx * (x + 5.2), sz * (z + 2.4)),
                        (sx * (x + 5.2), sz * (z + 5.4)),
                    ],
                    0.065,
                )
    print(f"FLOOR null rifts {_null_rifts(m)}")
    return [Part("FLOOR_NULL_MARBLE", "ARENA_FLOOR", m)]


def _obelisk(m, x, z, height, yaw):
    """上下收尖的八面悬浮石碑；底尖离台座两米，细嵌纹不替代石材轮廓。"""
    with m.at((x, 0, z), yaw):
        m.box(STONE, (4.0, 0.65, 4.0), chamfer=0.12)
        m.box(TRIM, (3.6, 0.08, 3.6), pos=(0, 0.65, 0), chamfer=0.03)
        # 环形石座顶面保留空隙，与悬浮主体明确分开。
        m.lathe(
            BLACK,
            [(1.35, 0.72), (1.20, 0.87), (0.70, 0.87), (0.70, 0.72)],
            16,
            smooth=False,
            cap_top=False,
            cap_bottom=False,
        )
        m.stack_rect(
            STONE,
            1.15,
            0.92,
            [
                (1.14, 2.25),
                (0.18, 3.40),
                (0, 4.00),
                (0.18, height - 2.0),
                (1.14, height),
            ],
            tint=(0.88, 0.88, 0.94),
        )
        for sx in (-1, 1):
            _beam(
                m, TRIM, (sx * 0.88, 4.1, 0.93), (sx * 0.75, height - 2.2, 0.75), 0.12
            )
            _beam(
                m, SEAM, (sx * 0.40, 4.4, 0.95), (sx * 0.34, height - 3.3, 0.84), 0.055
            )
        # 三段浮起的铭牌 / 腰环强化整体比例，微光只给窄刻线。
        for yy in (4.5, height * 0.55, height - 2.4):
            m.box(TRIM, (2.16, 0.12, 1.78), pos=(0, yy, 0), chamfer=0.04)
            _beam(m, SEAM, (-0.40, yy + 0.15, 0.925), (0.40, yy + 0.15, 0.925), 0.045)
        _beam(m, SEAM, (0, 2.3, 0), (0, 0.92, 0), 0.035)


def _throne(m):
    """北侧远处空位王座：层层台阶、宽扶手、高背、七片冠棱与透空背框。"""
    with m.at((0, 0, -49.8)):
        for i in range(4):
            m.box(
                STONE,
                (19.0 - i * 1.6, 0.42, 8.2 - i * 0.95),
                pos=(0, i * 0.42, 0.6 - i * 0.30),
                chamfer=0.10,
            )
            m.box(
                TRIM,
                (18.7 - i * 1.6, 0.075, 0.12),
                pos=(0, i * 0.42 + 0.36, 4.56 - i * 0.78),
            )
        m.box(BLACK, (5.4, 2.8, 4.0), pos=(0, 1.68, -0.3), chamfer=0.20)
        m.box(STONE, (6.2, 0.65, 4.7), pos=(0, 4.2, -0.1), chamfer=0.15)
        for side in (-1, 1):
            m.box(STONE, (1.0, 4.3, 4.6), pos=(side * 3.4, 1.68, -0.2), chamfer=0.17)
            m.box(TRIM, (1.15, 0.22, 4.8), pos=(side * 3.4, 5.9, -0.2), chamfer=0.05)
            _beam(m, SEAM, (side * 3.42, 3.1, 2.15), (side * 3.42, 5.7, 2.15), 0.07)
        # 高背分层：外侧黑石框 / 暗铂棱 / 内部石板，王座本体没有整块自发光。
        V = [
            (-3.4, 4.4, -2.5),
            (3.4, 4.4, -2.5),
            (2.5, 13.8, -2.5),
            (0, 16.9, -2.5),
            (-2.5, 13.8, -2.5),
        ]
        W = [(x, y, z - 0.65) for x, y, z in V]
        m.solid(
            STONE,
            V + W,
            [
                [0, 1, 2, 3, 4],
                [9, 8, 7, 6, 5],
                [0, 5, 6, 1],
                [1, 6, 7, 2],
                [2, 7, 8, 3],
                [3, 8, 9, 4],
                [4, 9, 5, 0],
            ],
        )
        for i in range(5):
            _beam(m, TRIM, V[i], V[(i + 1) % 5], 0.20)
        for x in (-7, -4.7, 0, 4.7, 7):
            top = 19.8 - abs(x) * 0.75
            _beam(m, STONE, (x, 1.8, -3.2), (x * 0.65, top, -3.4), 0.48, 0.55)
            _beam(
                m,
                TRIM,
                (x - 0.18, 2.2, -2.91),
                (x * 0.65 - 0.18, top - 0.4, -3.11),
                0.085,
            )
        for x in (-2.4, 2.4):
            _beam(m, STONE, (x, 12.0, -3.3), (x * 0.45, 18.2, -3.4), 0.26)
        for a, b in [
            ((0, 7.2, -2.13), (-1.3, 9.0, -2.13)),
            ((-1.3, 9.0, -2.13), (0, 11.1, -2.13)),
            ((0, 11.1, -2.13), (1.3, 9, -2.13)),
            ((1.3, 9, -2.13), (0, 7.2, -2.13)),
        ]:
            _beam(m, SEAM, a, b, 0.09)
        # 后方透空的八角门框，负空间让王座从星空中读出来。
        arch = [
            (-12, 0, -5),
            (-12, 11, -5),
            (-7, 18, -5),
            (7, 18, -5),
            (12, 11, -5),
            (12, 0, -5),
        ]
        for a, b in zip(arch[:-1], arch[1:]):
            _beam(m, STONE, a, b, 0.85)
        for a, b in zip(arch[1:-2], arch[2:-1]):
            _beam(m, TRIM, a, b, 0.16)


def build_bounds():
    rim, royal, obelisks = Mesh(547), Mesh(557), Mesh(563)
    # 踏步状护沿全在边界外；内缘低、外侧落入黑色的星空带。
    for sign in (-1, 1):
        for z in np.arange(-38, 40, 4):
            rim.box(
                STONE, (0.90, 0.42, 3.94), pos=(sign * 44.65, 0, float(z)), chamfer=0.06
            )
            rim.box(TRIM, (0.08, 0.06, 3.82), pos=(sign * 44.25, 0.46, float(z)))
            # r2：r1 的 2.8 m 连续发光条在游戏里连成一条虚线，像界面边框；改为每块护沿一枚小方钉
            rim.box(SEAM, (0.16, 0.035, 0.16), pos=(sign * 44.25, 0.49, float(z)), yaw=math.pi / 4)
        for x in np.arange(-42, 44, 4):
            rim.box(
                STONE, (3.94, 0.42, 0.90), pos=(float(x), 0, sign * 40.65), chamfer=0.06
            )
            rim.box(TRIM, (3.82, 0.06, 0.08), pos=(float(x), 0.46, sign * 40.25))
            rim.box(SEAM, (0.16, 0.035, 0.16), pos=(float(x), 0.49, sign * 40.25), yaw=math.pi / 4)
    _throne(royal)
    # 东西各三座，北高南低；所有高碑都位于 z<40 的侧面与北排。
    for sign in (-1, 1):
        for x, z, h in [
            (49, -29, 14.5),
            (50, -7, 11.5),
            (50, 18, 9.4),
            (23, -48, 16.5),
        ]:
            _obelisk(obelisks, sign * x, z, h, sign * 0.16)
    for sign in (-1, 1):
        for x in (18, 32):
            rim.box(STONE, (4.0, 0.70, 3.0), pos=(sign * x, 0, 44.6), chamfer=0.15)
            rim.box(TRIM, (3.0, 0.10, 2.0), pos=(sign * x, 0.72, 44.6), chamfer=0.04)
    # 有烘焙接触阴影，但不把抛光大理石涂成厚重黑泥。
    C.bake_ao(
        [rim, royal, obelisks],
        skip_mats=(SEAM,),
        samples=10,
        dist=3,
        strength=0.38,
        seed=571,
    )
    return [
        Part("BOUNDS_NULL_BALUSTRADE", "ARENA_BOUNDS", rim),
        Part("BOUNDS_EMPTY_THRONE", "ARENA_BOUNDS", royal),
        Part("BOUNDS_FLOATING_OBELISKS", "ARENA_BOUNDS", obelisks),
    ]


def build_props():
    m, rng = Mesh(577), random.Random(577)
    pts = C.poisson(
        rng,
        48,
        lambda x, z: math.hypot(x, z) > 21 and abs(x) < 41 and abs(z) < 36.5,
        5.5,
        (-40, 40, -36, 36),
    )
    for i, (x, z) in enumerate(pts):
        s = rng.uniform(0.20, 0.50)
        m.rock(
            STONE,
            (s, s * 0.32, s * 0.7),
            (x, 0, z),
            seed=581 + i,
            yaw=rng.random() * math.tau,
            detail=0,
            jitter=0.18,
        )
        if i % 4 == 0:
            with m.at((x + 0.4, 0, z), rng.random() * math.tau):
                m.box(TRIM, (0.70, 0.055, 0.16), pos=(0, 0.04, 0), chamfer=0.02)
    C.bake_ao([m], samples=8, dist=0.65, strength=0.35, seed=593)
    return [Part("PROPS_MARBLE_SHARDS", "ARENA_PROPS", m)]


def build_lights():
    stars = Mesh(599)
    rng = np.random.default_rng(599)
    count = 0
    while count < 520:
        x, z = rng.uniform(-67, 67), rng.uniform(-63, 63)
        # 四边的星空，不只填四个角；活动范围内绝不放星点。
        if abs(x) < 46 and abs(z) < 42:
            continue
        r = rng.uniform(0.035, 0.105)
        if count % 19 == 0:
            r *= 1.6
        with stars.at((x, 0.024, z)):
            C.disc(
                stars, STAR, r, seg=6, rings=1, y=0, tint=(rng.uniform(0.45, 1),) * 3
            )
        count += 1
    # 王座后方两片轻薄斜光，低强度、顶点透明度收边。
    shafts = Mesh(607)
    for sign in (-1, 1):
        P, A, F = [], [], []
        for j in range(7):
            t = j / 6
            for k in range(5):
                u = k / 4 * 2 - 1
                P.append(
                    (sign * (9 - 2 * t) + u * (1 + 2 * t), 15 * (1 - t), -55 + 8 * t)
                )
                A.append((1 - abs(u)) * (1 - t) ** 2)
        for j in range(6):
            for k in range(4):
                a = j * 5 + k
                F.append([a, a + 1, a + 6, a + 5])
        shafts.add(np.array(P), F, SHAFT, alpha=np.array(A))
    return [
        Part("LIGHT_ASTRAL_EDGE", "ARENA_LIGHTS", stars),
        Part("LIGHT_THRONE_TWILIGHT", "ARENA_LIGHTS", shafts),
    ]


def build():
    parts = []
    for name, fn in [
        ("floor", build_floor),
        ("bounds", build_bounds),
        ("props", build_props),
        ("lights", build_lights),
    ]:
        if name in PARTS:
            parts += fn()
    return parts
