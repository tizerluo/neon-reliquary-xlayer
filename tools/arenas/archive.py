"""冰封档案馆（区域 1）· 场地配方。

接口（build_arena.py 调用）：MOOD / make_specs(texdir) / build() → [Part...]。
通用部分在 common.py（网格构建器 / 材质 / 装配 / 导出 / 散布 / AO），贴图配方在 archive_tex.py；
本文件照搬 cathedral.py 的“结构”：材质表 + 四个构建函数 + 布局表，造型与配色全部换成档案馆。

布局（游戏坐标，+X 东 / +Z 南 / −Z 北；屏幕上方 = 北）：
  可活动区域 |x| ≤ 44、|z| ≤ 40；护栏内侧贴着边界线（|x| = 44.1、|z| = 40.1）。
  北侧（离镜头最远，最入镜）：结冰书架墙（8–16 m，z ≈ −45，中间留缺口）+ 后排断裂拱廊 + 带高窗的后墙 + 斜挂 / 坠落的冰棱吊灯；
  东西两侧：横向的书架排（面朝南，才看得见）、倾倒的书架、散落成堆的书、冰封阅读台、雪堆；
  南侧（靠近镜头）：全部 ≤ 2 m（雪堆、矮书堆、碎冰、冰锥）。
"""

import json
import math
import os
import random

import numpy as np

from arenas import archive_tex as AT
from arenas import common as C
from arenas import textures as T
from arenas.common import (CLEAN_R, PLAY_X, PLAY_Z, MatSpec, Mesh, Part, clear_of_play, lin, poisson, rag, vnoise)

ID = "archive"
TITLE = "Frozen Archive"
MOOD = "#9ab7dd"
EMBLEM_CENTER = (0.0, 0.0)

FLOOR = "Arena Floor Ice"
EMBLEM = "Arena Emblem Astrolabe"
STONE = "Arena Stone Frozen"
WOOD = "Arena Shelf Wood"
BOOKS = "Arena Book Wall"
ICE = "Arena Ice Crust"
SNOW = "Arena Snow Drift"
BRASS = "Arena Brass Old"
RUNE = "Arena Rune Trace"
PANE = "Arena Window Pane"
SHAFT = "Arena Shaft Frost"

EDGE_X, EDGE_Z = PLAY_X + 0.1, PLAY_Z + 0.1       # 护栏内侧
RIM_W = 1.2                                        # 护栏宽度
TAU = math.tau
PARTS = os.environ.get("ARENA_PARTS", "floor,bounds,props,lights").split(",")
BOOKS_GAIN, STONE_GAIN = 1.9, 1.5                    # 书架墙 / 冻石贴图的整体提亮（边界布景要读得出来，但仍比地面“沉”）
TEX_GAIN = 0.40                                    # 地面 / 纹章基础色整体压暗（顶点色乘数因此更大，8 位量化更细）
REF = dict(floor=0.32 * TEX_GAIN, emblem=0.30 * TEX_GAIN)     # 贴图平均线性明度（make_specs 里按实测更新）


# =====================================================================
# 材质与贴图
# =====================================================================
def _down2(a):
    n = a.shape[0] // 2
    return a.reshape(n, 2, n, 2, -1).astype(np.float64).mean(axis=(1, 3))


def _resize(a, m):
    """周期取样的缩放（n×n×c → m×m×c；先按比例轻模糊再双线性）：纹章基础色 1024² → 768² 省体积（冰下的星盘本来就是糊的）。"""
    n = a.shape[0]
    xs = (np.arange(m) + 0.5) / m
    X, Y = np.meshgrid(xs, xs)
    k = n / m
    return np.stack([T.sample_periodic(T.blur_periodic(a[..., c], 0.45 * k), X, Y) for c in range(a.shape[-1])], axis=-1)


def make_specs(texdir):
    """生成贴图并返回 {材质名: MatSpec}。ARENA_TEXCACHE=1 且贴图都在时直接复用（调试用）。"""
    names = ["floor_base", "floor_normal", "floor_mr", "emblem_base", "emblem_normal", "emblem_mr", "emblem_emissive", "stone_base", "stone_normal",
             "books_base", "books_normal", "ice_normal"]
    meta = texdir / "_meta.json"
    sizes = {}
    if os.environ.get("ARENA_TEXCACHE") == "1" and meta.exists() and all((texdir / f"{k}.png").exists() for k in names):
        info = json.loads(meta.read_text())
        REF.update(info["ref"])
        sizes = {k: (texdir / f"{k}.png").stat().st_size for k in names}
    else:
        def put(name, arr):
            sizes[name[:-4]] = T.write_png(texdir / name, arr)

        fl = AT.make_floor()
        put("floor_base.png", T.to_u8(T.lin_to_srgb(T.srgb_to_lin(fl["base"] / 255.0) * TEX_GAIN)))
        put("floor_normal.png", fl["normal"])
        put("floor_mr.png", fl["mr"])
        emb = AT.make_emblem()
        en = _down2(emb["normal"] / 255.0 * 2 - 1)
        en = en / np.linalg.norm(en, axis=-1, keepdims=True)
        put("emblem_base.png", T.to_u8(_resize(T.lin_to_srgb(T.srgb_to_lin(emb["base"] / 255.0) * TEX_GAIN), 768)))
        put("emblem_normal.png", T.to_u8(en * 0.5 + 0.5))
        er = _down2(emb["rough"][..., None])[..., 0]
        put("emblem_mr.png", T.to_u8(np.stack([np.zeros_like(er), er, np.zeros_like(er)], axis=-1)))
        put("emblem_emissive.png", T.to_u8(_down2(emb["emissive"] / 255.0)[..., :3]))
        st = AT.make_stone()
        put("stone_base.png", T.to_u8(T.lin_to_srgb(np.clip(T.srgb_to_lin(st["base"] / 255.0) * STONE_GAIN, 0, 1))))
        put("stone_normal.png", st["normal"])
        bk = AT.make_bookwall()
        put("books_base.png", T.to_u8(T.lin_to_srgb(np.clip(T.srgb_to_lin(bk["base"] / 255.0) * BOOKS_GAIN, 0, 1))))
        put("books_normal.png", bk["normal"])
        put("ice_normal.png", AT.make_ice_normal()["normal"])
        REF.update(floor=fl["stats"]["ref"] * TEX_GAIN, emblem=emb["stats"]["ref"] * TEX_GAIN)
        meta.write_text(json.dumps(dict(ref=dict(REF), items=fl["stats"]["items"], emblem_gem=emb["stats"]["gem"])))
    print("TEXTURES", {k: f"{v / 1024:.0f}KB" for k, v in sizes.items()}, "ref", {k: round(v, 4) for k, v in REF.items()})
    p = lambda k: texdir / f"{k}.png"
    return {
        FLOOR: MatSpec(FLOOR, tex=dict(base=p("floor_base"), normal=p("floor_normal"), mr=p("floor_mr")), uv="floor", uv_scale=AT.TILE_M,
                       normal_strength=AT.NORMAL_K),
        EMBLEM: MatSpec(EMBLEM, tex=dict(base=p("emblem_base"), normal=p("emblem_normal"), mr=p("emblem_mr"), emissive=p("emblem_emissive")), strength=0.35,
                        uv="floor", uv_scale=2 * AT.EMBLEM_R, uv_offset=(0.5, 0.5), normal_strength=AT.NORMAL_K),
        STONE: MatSpec(STONE, tex=dict(base=p("stone_base"), normal=p("stone_normal")), rough=0.72, uv="box", uv_scale=AT.STONE_M),
        WOOD: MatSpec(WOOD, base="#6b5646", rough=0.82),
        BOOKS: MatSpec(BOOKS, tex=dict(base=p("books_base"), normal=p("books_normal")), rough=0.72, uv="box", uv_scale=AT.SHELF_M),
        ICE: MatSpec(ICE, base="#5a6879", rough=0.28, tex=dict(normal=p("ice_normal")), uv="box", uv_scale=AT.ICE_M, normal_strength=1.0),
        SNOW: MatSpec(SNOW, base="#575e69", rough=0.93),
        BRASS: MatSpec(BRASS, base="#7d6038", metal=0.8, rough=0.46),
        RUNE: MatSpec(RUNE, base="#000000", emit="#93acd4", strength=0.38, rough=1.0),
        PANE: MatSpec(PANE, base="#0d1219", emit="#a8c2ea", strength=0.8, double=True, rough=0.3),
        # 光柱：半透明、双面、发光已按透明度预乘；透明度的渐隐由顶点色 A 给出
        SHAFT: MatSpec(SHAFT, base="#000000", emit="#a4bfe8", strength=round(1.5 * 0.36, 3), alpha=0.36, vcolor_alpha=True, rough=1.0),
    }


# =====================================================================
# 通用小件
# =====================================================================
def paint_mats(m, fn, mats):
    """只给指定材质的顶点乘 fn(P)（Mesh.paint 会动所有材质；冰 / 雪不该被“脏污”压暗）。"""
    P = np.concatenate(m.P)
    sel = np.zeros(len(P), bool)
    for mat, ids, *_ in m.F:
        if mat in mats:
            sel[ids] = True
    mult = fn(P)
    start = 0
    for W, Cc in zip(m.P, m.C):
        k = len(W)
        s = sel[start:start + k]
        Cc[s, :3] *= mult[start:start + k][s]
        start += k


def ice_tint(rng, lo=0.78, hi=1.05):
    t = rng.uniform(lo, hi)
    return (t * 0.92, t * 0.99, t * 1.08)


def snow_tint(rng, lo=0.85, hi=1.05):
    t = rng.uniform(lo, hi)
    return (t * 0.97, t * 1.0, t * 1.05)


def icicle(m, x, y_top, z, length, r, rng, sides=5):
    """挂在 (x, y_top, z) 下面的冰棱（尖朝下）。"""
    t = ice_tint(rng)
    length = min(length, y_top - 0.03)
    if length < 0.08:
        return
    with m.at((x, y_top - length, z)):
        if length > 0.9 and sides >= 5:
            m.lathe(ICE, [(0.0, 0.0), (r * 0.45, length * 0.42), (r, length)], sides, smooth=True, share=True, cap_bottom=False, cap_top=False, tint=t)
        else:
            m.lathe(ICE, [(0.0, 0.0), (r, length)], 4, smooth=True, share=True, cap_bottom=False, cap_top=False, tint=t)


def ice_shard(m, x, z, h, r, rng, tilt=0.25, sides=5):
    """立着的冰锥 / 碎冰（尖朝上，可微倾）。"""
    with m.at((x, -0.05, z), rng.uniform(0, TAU), rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt)):
        m.lathe(ICE, [(r, 0.0), (r * 0.6, h * 0.45), (0.0, h)], sides, smooth=False, cap_bottom=False, cap_top=False, tint=ice_tint(rng))


def ice_blob(m, x, y, z, rx, ry, rz, rng, seed=None, tint=None, detail=0, squash=0.6, sink=0.3, jitter=0.28, yaw=None):
    m.rock(ICE, (rx, ry, rz), (x, y, z), seed=rng.randint(0, 99999) if seed is None else seed, detail=detail, jitter=jitter, squash=squash,
           yaw=rng.uniform(0, TAU) if yaw is None else yaw, tint=tint or ice_tint(rng), sink=sink)


def drift(m, x, z, rx, rz, h, rng, ymax=None, detail=1, y=0.0, free=False):
    """雪堆：低矮的圆润土丘（车削的半个椭球，半径带起伏）。长条形的只允许小角度旋转；free=True 表示在草稿网格 / 局部坐标里放（不查可活动区域）。
    落点检查：整个椭圆足迹要在“可活动区域外扩 1.5 m”之外（高 ≤ 1.35 m 的只需外扩 0.05 m），否则略过。"""
    if ymax is not None:
        h = min(h, ymax)
    yaw = rng.uniform(0, TAU) if rx < rz * 1.25 and rz < rx * 1.25 else rng.uniform(-0.18, 0.18) + (math.pi if rng.random() < 0.5 else 0.0)
    if not free:
        ex = 1.15 * math.hypot(rx * math.cos(yaw), rz * math.sin(yaw))
        ez = 1.15 * math.hypot(rx * math.sin(yaw), rz * math.cos(yaw))
        lim = 0.05 if h <= 1.35 else 1.5
        if not (abs(x) - ex >= PLAY_X + lim or abs(z) - ez >= PLAY_Z + lim):
            return
    sides = {0: 6, 1: 9, 2: 12}[detail]
    rmod = [rng.uniform(0.82, 1.1) for _ in range(sides)]
    prof = {0: [(1.0, 0.0), (0.78, 0.60), (0.0, 1.0)],
            1: [(1.0, 0.0), (0.9, 0.40), (0.56, 0.82), (0.0, 1.0)],
            2: [(1.0, 0.0), (0.95, 0.32), (0.74, 0.70), (0.42, 0.93), (0.0, 1.0)]}[detail]
    with m.at((x, y, z), yaw):
        m.lathe(SNOW, [(r, yy * h) for r, yy in prof], sides, smooth=True, share=True, ellipse=(rx, rz), rmod=rmod, cap_bottom=False, cap_top=False,
                tint=snow_tint(rng))


BOOK_TINTS = [(0.95, 0.80, 0.68), (0.75, 0.82, 1.0), (0.85, 0.95, 0.80), (1.05, 0.72, 0.66), (0.9, 0.9, 0.95), (1.0, 0.92, 0.75), (0.7, 0.7, 0.78)]


def book(m, rng, x, y, z, yaw, pitch=0.0, roll=0.0, scale=1.0):
    w, h, t = rng.uniform(0.17, 0.27) * scale, rng.uniform(0.04, 0.075) * scale, rng.uniform(0.24, 0.36) * scale
    k = rng.uniform(0.7, 1.1)
    tc = rng.choice(BOOK_TINTS)
    m.box(BOOKS, (w, h, t), pos=(x, y, z), yaw=yaw, pitch=pitch, roll=roll, bottom=False, tint=(tc[0] * k, tc[1] * k, tc[2] * k))


def book_heap(m, x, z, radius, n, hmax, seed, ymax=None):
    """散落成堆的书：大小相近的长方体随机朝向、随堆高抬起；总高 ≤ ymax；落进“可活动区域外扩 1.5 m”的直接略过。"""
    rng = random.Random(seed)
    for i in range(n):
        d = radius * (rng.random() ** 0.8)
        a = rng.uniform(0, TAU)
        prof = hmax * (1.0 - d / radius) ** 1.2
        y0 = prof * 0.78 + rng.uniform(0.0, 0.10)
        if ymax is not None:
            y0 = min(y0, max(0.0, ymax - 0.30))
        px_, pz_ = x + d * math.cos(a), z + d * math.sin(a)
        if not clear_of_play(px_, pz_, 0.4):
            continue
        tilt = 0.55 * (1.0 - d / radius) + 0.12
        book(m, rng, px_, y0, pz_, rng.uniform(0, TAU), rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt))
    # 几张散页（压在书堆边缘的地上）
    for _ in range(max(2, n // 12)):
        a, d = rng.uniform(0, TAU), radius * rng.uniform(0.7, 1.25)
        px_, pz_ = x + d * math.cos(a), z + d * math.sin(a)
        if clear_of_play(px_, pz_, 0.4):
            page(m, rng, px_, pz_)


def page(m, rng, x, z, size=1.0):
    w, h = rng.uniform(0.2, 0.3) * size, rng.uniform(0.28, 0.4) * size
    a = rng.uniform(0, TAU)
    ca, sa = math.cos(a), math.sin(a)
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    y = 0.012 + rng.uniform(0, 0.012)
    t = rng.uniform(0.62, 0.86)
    m.quad_up(SNOW, [(x + px * ca - pz * sa, y, z + px * sa + pz * ca) for px, pz in pts], tint=(t * 1.0, t * 0.93, t * 0.80))


def grounded(tmp, pos, m, dy=0.0, must_clear=True):
    """把草稿网格 tmp 落地（最低点贴 y = dy）并入 m。must_clear：整体不能压进“可活动区域外扩 1.5 m”的范围，否则放弃（返回 False）。"""
    if must_clear:
        P = np.concatenate(tmp.P)
        if not np.all((np.abs(P[:, 0] + pos[0]) >= PLAY_X + 1.5) | (np.abs(P[:, 2] + pos[1]) >= PLAY_Z + 1.5)):
            return False
    m.absorb(tmp, (pos[0], dy - tmp.min_y(), pos[1]))
    return True


# =====================================================================
# 书架 / 拱廊 / 梁 / 吊灯
# =====================================================================
def shelf_wall(m, x0, x1, z, top_fn, seed, bay=2.7, depth=0.55, hmin=3.0, ice_k=1.0, board_ice_below=10.0, crust_k=2.0):
    """结冰书架墙（沿 x，背面中线在 z，正面朝 +Z；必须 x0 < x1）。每开间：书背板（3 条竖条，顶部参差）+ 木立柱（不高过相邻背板）+
    每 2 m 一块层板（只在背板高度以下）+ 层板上的雪 / 下面的冰棱 + 贴在书面上的冰壳。top_fn(x) = 该处的墙高。"""
    assert x1 > x0
    rng = random.Random(seed)
    nb = max(1, int(round((x1 - x0) / bay)))
    w = (x1 - x0) / nb
    ns = 3
    sw = w / ns
    H = [[max(hmin, top_fn(x0 + b * w + (s + 0.5) * sw) - rag((x0 + b * w + (s + 0.5) * sw) * 1.3, seed * 3 + s, 3.4) * (0.4 + 0.6 * rng.random()))
          for s in range(ns)] for b in range(nb)]
    for b in range(nb):
        xa, xb = x0 + b * w, x0 + (b + 1) * w
        xc = (xa + xb) / 2
        uvo = (rng.random(), rng.randint(0, 31) / 32.0)
        for s in range(ns):
            xs = xa + (s + 0.5) * sw
            hs = H[b][s]
            t = rng.uniform(0.82, 1.08)
            m.box(BOOKS, (sw * 0.998, hs, depth), pos=(xs, 0, z + rng.uniform(-0.04, 0.04)), bottom=False, uvoff=uvo, tint=(t, t, t))
            if rng.random() < 0.7:           # 顶上的积雪
                m.box(SNOW, (sw * 0.96, rng.uniform(0.08, 0.2), depth * 0.9), pos=(xs, hs, z), chamfer=0.04, tint=snow_tint(rng))
            k = 1
            while 2.0 * k < hs - 0.8:        # 层板（只在本条背板的高度以下）
                y = 2.0 * k - 0.05
                k += 1
                if rng.random() < 0.10:
                    continue
                m.box(WOOD, (sw * 0.995, 0.10, depth + 0.55), pos=(xs, y, z + 0.28), bottom=True, tint=(0.9, 0.9, 0.92))
                low = y < board_ice_below
                if low and rng.random() < 0.55:
                    drift(m, xs + rng.uniform(-0.2, 0.2), z + 0.42, sw * 0.40, 0.20, 0.10, rng, detail=0, y=y + 0.10, free=True)
                for _ in range(int(round((rng.randint(1, 3) if low else rng.randint(0, 1)) * ice_k))):
                    ln = rng.uniform(0.25, 1.1) if rng.random() > 0.14 else rng.uniform(1.6, 3.4)
                    icicle(m, xa + s * sw + rng.uniform(0.1, sw - 0.1), y, z + 0.28 + (depth + 0.55) / 2 - rng.uniform(0.03, 0.15), ln, rng.uniform(0.05, 0.11) * (1 + 0.2 * ln), rng,
                           sides=5 if low else 4)
        # 立柱：每个开间的左边界（最后一个开间再加右边界）；不高过相邻背板
        for x, left_i, right_i in ([(xa, b - 1, b)] + ([(xb, b, None)] if b == nb - 1 else [])):
            nbr = []
            if left_i is not None and left_i >= 0:
                nbr.append(H[left_i][-1])
            if right_i is not None:
                nbr.append(H[right_i][0])
            hp = max(hmin, min(nbr) * rng.uniform(0.86, 1.0))
            t = rng.uniform(0.85, 1.1)
            m.box(WOOD, (0.34, hp, depth + 0.30), pos=(x, 0, z + 0.15), bottom=False, tint=(t, t, t))
        # 贴在书面上的冰壳（宽而薄的竖向椭球）
        for _ in range(int(round(rng.randint(1, 2) * crust_k))):
            s = rng.randrange(ns)
            hh = rng.uniform(0.7, 2.0)
            top_s = H[b][s]
            y0 = rng.uniform(0.0, max(0.1, top_s - hh * 2.1 - 0.8))
            ice_blob(m, xa + (s + 0.5) * sw + rng.uniform(-0.2, 0.2), y0, z + depth / 2 + 0.02, rng.uniform(0.40, 0.80), hh, rng.uniform(0.12, 0.20), rng, squash=1.0,
                     sink=1.0, jitter=0.22)
        # 墙脚雪堆
        if rng.random() < 0.7:
            drift(m, xc + rng.uniform(-0.4, 0.4), z + 1.5, w * 0.62, rng.uniform(0.9, 1.5), rng.uniform(0.5, 1.2), rng)


def pier(m, x, z, r, h, seed, broken=True):
    """八角墩柱：柱础 + 柱身（略收分）+ 柱头（完整）或锯齿断口（断裂）。局部原点 = 柱底中心；返回柱顶高度。"""
    rng = random.Random(seed)
    with m.at((x, 0, z), rng.uniform(0, 1)):
        m.lathe(STONE, [(r * 1.5, 0.0), (r * 1.5, 0.55), (r * 1.12, 0.78)], 8, smooth=False, rot=math.pi / 8, cap_bottom=False, cap_top=False)
        top = h - (1.0 if not broken else 0.0)
        jag = (min(0.9 * r + 0.25, 1.4), seed * 7) if broken else None
        t = rng.uniform(0.9, 1.08)
        m.lathe(STONE, [(r, 0.78), (r * 0.94, top)], 8, smooth=False, rot=math.pi / 8, cap_bottom=False, cap_top=bool(jag), top_jag=jag, tint=(t, t, t))
        if not broken:
            m.lathe(STONE, [(r * 0.98, top), (r * 1.25, top + 0.4), (r * 1.55, top + 1.0)], 8, smooth=False, rot=math.pi / 8, cap_bottom=False, cap_top=True)
        if rng.random() < 0.7:               # 柱身中段的冰壳
            ice_blob(m, rng.uniform(-0.3, 0.3), rng.uniform(1.0, 3.0), rng.uniform(0.2, 0.5), r * 0.55, rng.uniform(0.8, 2.0), r * 0.35, rng, squash=1.0, sink=1.0)
    return h


def _wedge(m, mat, cx, cy, a0, a1, r0, r1, z0, z1, tint, wreck=None):
    def pt(t_, rad, zz):
        return np.array([cx + rad * math.cos(t_), cy + rad * math.sin(t_), zz])
    V = np.array([pt(a0, r0, z0), pt(a1, r0, z0), pt(a1, r1, z0), pt(a0, r1, z0), pt(a0, r0, z1), pt(a1, r0, z1), pt(a1, r1, z1), pt(a0, r1, z1)])
    if wreck:
        rng, amp = wreck
        for j in (1, 2, 5, 6):
            V[j] += rng.uniform(-amp, amp, 3) * np.array([1, 1, 0.5])
    m.solid(mat, V, [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [3, 2, 6, 7], [0, 3, 7, 4], [1, 2, 6, 5]], ref=V.mean(axis=0), tint=tint)


def round_arch(m, xa, xb, y0, z, depth, thick, seed, keep_a=1.0, keep_b=1.0, n=12):
    """半圆拱（拱面在 z 平面）：跨 [xa, xb]、起拱高 y0。keep_a / keep_b：左 / 右半拱保留的比例（断拱）；断口顶点被打乱；顶上的积雪。"""
    R = (xb - xa) / 2
    cx = (xa + xb) / 2
    rng = np.random.default_rng(abs(seed))
    half = n // 2
    for side, keep in ((0, keep_a), (1, keep_b)):
        nk = int(math.ceil(half * keep - 1e-6))
        for i in range(nk):
            if side == 0:
                a0, a1 = math.pi - i * math.pi / n, math.pi - (i + 1) * math.pi / n
            else:
                a0, a1 = i * math.pi / n, (i + 1) * math.pi / n
            tt = 0.88 + 0.2 * rng.random()
            last = (i == nk - 1 and keep < 1.0)
            _wedge(m, STONE, cx, y0, a0, a1, R - thick * 0.5, R + thick * 0.5, z - depth / 2, z + depth / 2, (tt,) * 3, wreck=(rng, 0.4) if last else None)
            if rng.random() < 0.45:
                _wedge(m, SNOW, cx, y0, a0, a1, R + thick * 0.45, R + thick * 0.62, z - depth * 0.40, z + depth * 0.40, (0.95,) * 3)


def beam_out(m, x, y, z, length, rng, droop=0.06, thick=0.42):
    """从书架墙顶伸出（朝 +Z）的残梁；末端断口；返回梁末端的 (x, y, z)。"""
    with m.at((x, y, z), 0.0, -droop):
        m.box(WOOD, (thick, thick * 1.15, length), pos=(0, 0, length / 2), anchor="center", tint=(0.95, 0.95, 0.98))
    ex, ey, ez = x, y - math.sin(droop) * length, z + math.cos(droop) * length
    drift(m, x, z + length * 0.4, thick * 0.55, length * 0.38, 0.09, rng, detail=0, y=y + thick * 0.57, free=True)
    for _ in range(4):
        icicle(m, x + rng.uniform(-0.15, 0.15), y - thick * 0.5, z + rng.uniform(0.3, length - 0.1), rng.uniform(0.3, 1.1), rng.uniform(0.05, 0.1), rng)
    return ex, ey, ez


def chandelier(m, x, y, z, R, rng, tilt=0.0, roll=0.0, yaw=0.0, chain_from=None):
    """冰棱吊灯：铁圈 + 6–8 根灯臂（烛杯 + 发光冰晶）+ 垂坠的冰晶串 + 冰壳 + 下垂冰棱；chain_from = 吊链上端 (x, y, z)。局部原点 = 圈心。"""
    with m.at((x, y, z), yaw, tilt, roll):
        rr = 0.075
        m.lathe(BRASS, [(R, -rr), (R + rr, 0.0), (R, rr), (R - rr, 0.0), (R, -rr)], 10, smooth=True, share=True, cap_bottom=False, cap_top=False)
        m.lathe(BRASS, [(0.0, -0.5), (0.18, -0.35), (0.10, -0.1), (0.28, 0.12), (0.0, 0.55)], 8, smooth=True, share=True, cap_bottom=False, cap_top=False)   # 中央坠球
        arms = rng.randint(6, 8)
        for k in range(arms):
            a = k * TAU / arms + rng.uniform(-0.1, 0.1)
            ax, az = math.cos(a), math.sin(a)
            # 灯臂（从中央到圈）
            with m.at((0, 0, 0), -a + math.pi / 2):
                m.box(BRASS, (0.05, 0.05, R), pos=(0, 0, R / 2), anchor="center")
            # 烛杯 + 冰晶（灯里的“火”）
            cx, cz = ax * R, az * R
            with m.at((cx, 0.03, cz)):
                m.lathe(BRASS, [(0.05, 0.0), (0.11, 0.11), (0.10, 0.17)], 6, smooth=False, cap_bottom=True, cap_top=False)
                s = rng.uniform(0.16, 0.26)
                V = np.array([(0, 0.18, 0), (0, 0.18 + s * 2.4, 0), (s * 0.5, 0.18 + s * 0.9, 0), (-s * 0.5, 0.18 + s * 0.9, 0), (0, 0.18 + s * 0.9, s * 0.5), (0, 0.18 + s * 0.9, -s * 0.5)])
                m.solid(PANE, V, [[0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2], [1, 2, 4], [1, 4, 3], [1, 3, 5], [1, 5, 2]], ref=(0, 0.18 + s * 0.9, 0))
            # 垂坠的冰晶串（发光）
            if rng.random() < 0.75:
                for j in range(rng.randint(1, 2)):
                    ln = rng.uniform(0.25, 0.6)
                    px_, pz_ = ax * (R + 0.02 + 0.08 * j), az * (R + 0.02 + 0.08 * j)
                    with m.at((px_, -rr, pz_)):
                        s = ln * 0.18
                        V = np.array([(0, 0, 0), (0, -ln, 0), (s, -ln * 0.3, 0), (-s, -ln * 0.3, 0), (0, -ln * 0.3, s), (0, -ln * 0.3, -s)])
                        m.solid(PANE, V, [[0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2], [1, 2, 4], [1, 4, 3], [1, 3, 5], [1, 5, 2]], ref=(0, -ln * 0.3, 0))
        # 冰壳：圈上的几团冰 + 下垂冰棱
        for _ in range(rng.randint(3, 6)):
            a = rng.uniform(0, TAU)
            ice_blob(m, math.cos(a) * R, -0.12, math.sin(a) * R, rng.uniform(0.18, 0.34), rng.uniform(0.18, 0.34), rng.uniform(0.18, 0.34), rng, squash=0.9, sink=0.3)
        for _ in range(rng.randint(8, 14)):
            a = rng.uniform(0, TAU)
            rad = R + rng.uniform(-0.06, 0.06)
            icicle(m, math.cos(a) * rad, -0.05, math.sin(a) * rad, rng.uniform(0.3, 1.0), rng.uniform(0.04, 0.09), rng, sides=4)
    if chain_from is not None:
        fx, fy, fz = chain_from
        p0 = np.array([fx, fy, fz])
        for k in range(3):                   # 三根吊链连到圈上
            a = k * TAU / 3 + 0.4
            local = np.array([math.cos(a) * R, 0.0, math.sin(a) * R])
            with m.at((x, y, z), yaw, tilt, roll):
                p1 = m.world(local)
            d = p0 - p1
            L = float(np.linalg.norm(d))
            yaw_ = math.atan2(d[0], d[2])
            pitch_ = -math.asin(d[1] / max(L, 1e-6))
            with m.at(p1, yaw_, pitch_):
                m.box(BRASS, (0.05, 0.05, L), pos=(0, 0, L / 2), anchor="center", tint=(0.8, 0.8, 0.85))


def reading_desk(m, x, z, yaw, seed, ymax=None):
    """冰封的阅读台：两块侧板 + 斜面书桌 + 下搁板 + 凳子 + 桌上的书；覆着冰壳 / 雪，桌沿垂冰棱。"""
    rng = random.Random(seed)
    s = 1.0 if ymax is None else min(1.0, (ymax - 0.15) / 1.5)
    tmp = Mesh(seed)
    with tmp.at((0, 0, 0), yaw, 0.0, 0.0, s):
        for sx in (-0.95, 0.95):
            tmp.box(WOOD, (0.12, 1.05, 0.78), pos=(sx, 0, 0), bottom=False, chamfer=0.02)
        tmp.box(WOOD, (1.9, 0.05, 0.62), pos=(0, 0.32, 0.0), anchor="center")
        with tmp.at((0, 1.04, 0.0), 0.0, 0.22):
            tmp.box(WOOD, (2.15, 0.09, 0.95), pos=(0, 0, 0), anchor="center", chamfer=0.0)
            for _ in range(rng.randint(2, 4)):
                book(tmp, rng, rng.uniform(-0.8, 0.8), 0.04, rng.uniform(-0.3, 0.3), rng.uniform(0, TAU), 0.0, 0.0)
            drift(tmp, rng.uniform(-0.5, 0.5), rng.uniform(-0.1, 0.1), 0.8, 0.34, 0.09, rng, detail=0, y=0.045, free=True)
            for _ in range(rng.randint(5, 8)):
                icicle(tmp, rng.uniform(-1.0, 1.0), -0.04, 0.46, rng.uniform(0.15, 0.5), rng.uniform(0.04, 0.07), rng, sides=4)
        with tmp.at((1.5, 0, 0.9)):
            tmp.lathe(WOOD, [(0.2, 0.0), (0.16, 0.5), (0.22, 0.56)], 8, smooth=True, share=False, cap_bottom=False, cap_top=True)
        ice_blob(tmp, rng.uniform(-0.8, 0.8), 0.0, 0.55, 0.45, 0.35, 0.28, rng, squash=0.8, sink=0.2)
    grounded(tmp, (x, z), m)


def toppled_shelf(m, x, z, yaw, tilt, seed, w=2.6, h=4.6, ymax=None):
    """倾倒的书架（侧翻 / 斜靠）：书背板 + 两块侧板 + 层板，冰壳 + 冰棱。"""
    rng = random.Random(seed)
    tmp = Mesh(seed)
    with tmp.at((0, 0, 0), yaw, tilt, rng.uniform(-0.12, 0.12)):
        tmp.box(BOOKS, (w, h, 0.4), pos=(0, 0, 0), bottom=False, uvoff=(rng.random(), rng.randint(0, 31) / 32.0))
        for sx in (-w / 2, w / 2):
            tmp.box(WOOD, (0.14, h, 0.9), pos=(sx, 0, 0.3), bottom=False)
        for k in range(1, int(h / 1.1)):
            tmp.box(WOOD, (w, 0.08, 0.85), pos=(0, 1.1 * k, 0.28), bottom=True)
        for _ in range(rng.randint(5, 9)):
            icicle(tmp, rng.uniform(-w / 2, w / 2), 1.1 * rng.randint(1, max(1, int(h / 1.1) - 1)), 0.72, rng.uniform(0.3, 0.9), rng.uniform(0.05, 0.1), rng)
        for _ in range(2):
            ice_blob(tmp, rng.uniform(-w / 2 + 0.3, w / 2 - 0.3), rng.uniform(0.3, h * 0.6), 0.28, rng.uniform(0.3, 0.55), rng.uniform(0.6, 1.3), 0.2, rng, squash=1.0, sink=1.0)
    hh = max(W[:, 1].max() for W in tmp.P) - tmp.min_y()
    if ymax is not None and hh > ymax:
        return
    if not grounded(tmp, (x, z), m):
        return
    # 掉出来的书
    book_heap(m, x + rng.uniform(-0.6, 0.6), z + rng.uniform(-0.6, 0.6), rng.uniform(1.2, 1.8), rng.randint(14, 22), 0.5, seed * 3 + 1, ymax=ymax)


# =====================================================================
# 地面
# =====================================================================
_to_blender_orig = C.to_blender


def _to_blender_floor_warp(mesh, name, mats, specs, collection=None):
    """包装 common.to_blender（只在导入本区域时生效，不动共享模块）：给 FLOOR_ICE 里“地面冰板”材质的 UV 加上 AT.uv_warp 的低频位移，
    让 20 m 周期的贴图在 140 m 的地面上不铺成整齐的格子。纹章圆盘 / 符文线的 UV 不动。"""
    obj = _to_blender_orig(mesh, name, mats, specs, collection)
    if name != "FLOOR_ICE":
        return obj
    me = obj.data
    slots = [i for i, mt in enumerate(me.materials) if mt.name == FLOOR]
    if not slots:
        return obj
    nl, npoly = len(me.loops), len(me.polygons)
    vi = np.zeros(nl, np.int32)
    me.loops.foreach_get("vertex_index", vi)
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mi = np.zeros(npoly, np.int32)
    me.polygons.foreach_get("material_index", mi)
    lt = np.zeros(npoly, np.int32)
    me.polygons.foreach_get("loop_total", lt)
    sel = (mi[np.repeat(np.arange(npoly), lt)] == slots[0])
    uvl = me.uv_layers["UVMap"]
    uv = np.zeros(nl * 2, np.float32)
    uvl.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    dx, dz = AT.uv_warp(co[vi, 0], -co[vi, 1])           # Blender：x 东、y 北（= −z 游戏）
    uv[sel, 0] += (dx / AT.TILE_M)[sel]
    uv[sel, 1] -= (dz / AT.TILE_M)[sel]                  # v = −Z / s
    uvl.data.foreach_set("uv", uv.ravel())
    me.update()
    return obj


C.to_blender = _to_blender_floor_warp
_WARP_LOW = []

MACRO_STOPS = [(0.00, "#2c2c2e"), (0.30, "#2c2c30"), (0.58, "#2d2d31"), (0.78, "#2d2c30"), (0.92, "#2e2c30"), (1.00, "#2f2c2f")]
FLOOR_GAIN = float(os.environ.get("ARENA_FLOOR_GAIN", 2.3))       # 调亮度用（整个地面顶点色乘数）
GLYPHS = [
    [(0, -1, 0, 1), (0, 0, 0.8, -0.7)],
    [(-0.7, -1, -0.7, 1), (-0.7, 0, 0.7, -1), (-0.7, 0, 0.7, 1)],
    [(-0.8, -0.8, 0.8, 0.8), (-0.8, 0.8, 0.8, -0.8), (0, -1, 0, 1)],
    [(-0.7, -1, 0.7, -1), (0, -1, 0, 1), (-0.7, 1, 0.7, 1)],
    [(0, -1, 0.8, 0), (0.8, 0, 0, 1), (0, 1, -0.8, 0), (-0.8, 0, 0, -1)],
    [(-0.8, 0, 0.8, 0), (0, -1, 0, 0.2), (-0.5, -0.5, 0.5, -0.5)],
]


def _stroke(m, mat, x0, z0, x1, z1, hw, y):
    d = np.array([x1 - x0, z1 - z0])
    L = float(np.hypot(*d))
    if L < 1e-6:
        return
    d /= L
    nx_, nz_ = -d[1] * hw, d[0] * hw
    ex, ez = d[0] * hw, d[1] * hw
    m.quad_up(mat, [(x0 - ex + nx_, y, z0 - ez + nz_), (x1 + ex + nx_, y, z1 + ez + nz_), (x1 + ex - nx_, y, z1 + ez - nz_), (x0 - ex - nx_, y, z0 - ez - nz_)])


def follow_seams(W, tile_m=AT.TILE_M, step=0.55):
    """符文线要贴着“被弯曲过的接缝”：贴图里接缝 = 沃罗诺伊直边被 AT.warp_low 位移，世界里贴图又被 AT.uv_warp 位移。
    W = 沃罗诺伊直边上的折线（米，格点坐标）→ 加密后逐点反推到世界坐标。"""
    if not _WARP_LOW:
        _WARP_LOW.extend(AT.warp_low())
    wlx, wly = _WARP_LOW
    dense = []
    for (x0, z0), (x1, z1) in zip(W[:-1], W[1:]):
        k = max(1, int(math.ceil(math.hypot(x1 - x0, z1 - z0) / step)))
        dense += [(x0 + (x1 - x0) * j / k, z0 + (z1 - z0) * j / k) for j in range(k)]
    dense.append(W[-1])
    out = []
    for x, z in dense:
        fx, fz = (x / tile_m) % 1.0, (z / tile_m) % 1.0
        tx, tz = x - float(T.sample_periodic(wlx, fx, fz)), z - float(T.sample_periodic(wly, fx, fz))
        px, pz = tx, tz
        for _ in range(3):
            dx, dz = AT.uv_warp(px, pz)
            px, pz = tx - float(dx), tz - float(dz)
        out.append((px, pz))
    return out


def rune_lines(m, graph, tile_m, walks_per_tile, density_fn, exclude_r, seed=7100, hw=0.018, y=0.010):
    """冷白符文引导线：沿着冰板的接缝（graph = VoronoiGraph，种子与贴图一致）随机走几条，细窄带 + 刻度 + 端点符文。返回走线条数。"""
    ti0, ti1 = int(math.floor(-C.FLOOR_X / tile_m)), int(math.ceil(C.FLOOR_X / tile_m))
    tj0, tj1 = int(math.floor(-C.FLOOR_Z / tile_m)), int(math.ceil(C.FLOOR_Z / tile_m))
    count = 0
    for ti in range(ti0, ti1):
        for tj in range(tj0, tj1):
            rng = np.random.default_rng(seed + ti * 101 + tj * 7)
            cx, cz = (ti + 0.5) * tile_m, (tj + 0.5) * tile_m
            dout = max(abs(cx) - PLAY_X, abs(cz) - PLAY_Z, 0.0)
            k = 1.0 - 0.85 * float(T.smoothstep(0.0, 16.0, dout))
            n_walks = int(rng.poisson(walks_per_tile * k))
            done, tries = 0, 0
            while done < n_walks and tries < 60:
                tries += 1
                v = int(rng.integers(len(graph.pos)))
                lx, ly = graph.pos[v]
                if rng.random() > density_fn((ti + lx) * tile_m, (tj + ly) * tile_m):
                    continue
                pts = graph.walk(rng, v, int(rng.integers(2, 5)))
                W = [((ti + px_) * tile_m, (tj + py_) * tile_m) for px_, py_ in pts]
                if any(abs(x) > C.FLOOR_X - 0.5 or abs(z) > C.FLOOR_Z - 0.5 or math.hypot(x, z) < exclude_r for x, z in W):
                    continue
                W = follow_seams(W, tile_m)
                for (x0, z0), (x1, z1) in zip(W[:-1], W[1:]):
                    _stroke(m, RUNE, x0, z0, x1, z1, hw, y)
                    L = math.hypot(x1 - x0, z1 - z0)
                    d = np.array([x1 - x0, z1 - z0]) / max(L, 1e-6)
                    for j in range(int(L / 1.3)):          # 刻度：每 1.3 m 一道短横
                        t = (j + 0.5) * 1.3
                        px_, pz_ = x0 + d[0] * t, z0 + d[1] * t
                        _stroke(m, RUNE, px_ - d[1] * 0.11, pz_ + d[0] * 0.11, px_ + d[1] * 0.11, pz_ - d[0] * 0.11, hw * 0.7, y)
                for (x, z) in (W[0], W[-1]):
                    m.poly(RUNE, [(x + 0.075 * math.cos(a), y + 0.001, z - 0.075 * math.sin(a)) for a in np.linspace(0, math.tau, 7)[:-1]])
                # 端点旁的符文
                gx, gz = W[-1]
                g = GLYPHS[int(rng.integers(len(GLYPHS)))]
                ang = float(rng.uniform(0, TAU))
                sc = float(rng.uniform(0.11, 0.17))
                ca, sa = math.cos(ang), math.sin(ang)
                ox, oz = gx + 0.40 * math.cos(ang + 1.0), gz + 0.40 * math.sin(ang + 1.0)
                for (a0, b0, a1, b1) in g:
                    _stroke(m, RUNE, ox + (a0 * ca - b0 * sa) * sc, oz + (a0 * sa + b0 * ca) * sc, ox + (a1 * ca - b1 * sa) * sc, oz + (a1 * sa + b1 * ca) * sc, hw * 0.8, y)
                done += 1
                count += 1
    return count


def build_floor():
    """ARENA_FLOOR：整片冰板（3 m 网格，顶点色给钢蓝 / 灰蓝色相与明暗）+ 中央冰下星盘纹章（30 m 圆盘）+ 符文引导线几何。"""
    m = Mesh(11)
    P = C.floor_grid(m, FLOOR, 2.0)
    field = 0.62 * vnoise(P, 0.055, 31) + 0.28 * vnoise(P, 0.13, 32) + 0.10 * vnoise(P, 0.31, 33)
    pct = np.argsort(np.argsort(field)) / float(len(field) - 1)
    col = C.macro_color(pct, MACRO_STOPS, REF["floor"])
    big, mid = vnoise(P, 0.045, 5), vnoise(P, 0.16, 8)
    d_out = np.maximum(np.maximum(np.abs(P[:, 0]) - PLAY_X, np.abs(P[:, 2]) - PLAY_Z), 0.0)
    fade = 1.0 - 0.50 * T.smoothstep(0.0, 14.0, d_out)
    mk = float(os.environ.get("ARENA_MACRO", 1.0))
    v = (1.0 + mk * (-0.26 + 0.44 * big + 0.20 * mid)) * fade * FLOOR_GAIN                         # 宏观明暗：深冰 / 浅冰的大片变化（±25%）
    hue = (vnoise(P, 0.07, 41) - 0.5) * 0.14                                          # 色相：偏暖灰 ↔ 偏钢蓝的缓慢漂移（±7%）
    m.C[-1][:, :3] = np.clip(col * v[:, None] * np.stack([1 + hue, np.ones_like(hue), 1 - hue], axis=1), 0, 1)
    inside = np.hypot(P[:, 0], P[:, 2]) < AT.EMBLEM_R + 3.0
    avg = m.C[-1][inside, :3].mean(axis=0)
    emb_tint = tuple(np.clip(avg * REF["floor"] / REF["emblem"], 0, 1))
    C.disc(m, EMBLEM, AT.EMBLEM_R, tint=emb_tint, y=0.02)
    graph = T.VoronoiGraph(AT.FLOOR_CELLS, AT.FLOOR_JITTER, AT.FLOOR_SEED)          # 种子与贴图一致 → 引导线贴着冰板接缝
    dens = lambda x, z: 0.25 + 0.75 * float(T.smoothstep(0.30, 0.62, vnoise(np.array([[x, 0.0, z]]), 0.05, 3)[0]))
    n_runes = rune_lines(m, graph, AT.TILE_M, 1.1, dens, exclude_r=AT.EMBLEM_R + 2.2)
    print(f"FLOOR rune walks {n_runes}  floor color {tuple(round(float(c), 3) for c in avg)}")
    return [Part("FLOOR_ICE", "ARENA_FLOOR", m)]


# =====================================================================
# 边界与布景（ARENA_BOUNDS）
# =====================================================================
def parapet(m, length, seed):
    """沿一条边的低矮冰封石砌护栏（局部：x 沿边，z 向外，内侧面在 z = 0.1）。总高 ≤ 1.45 m；随机几处缺口（塌掉的石块 / 碎冰 / 书）。"""
    rng = random.Random(seed)
    L, x0 = length, -length / 2
    gaps, pos = [], x0 + rng.uniform(5, 12)
    while pos < L / 2 - 7:
        gl = rng.uniform(1.8, 5.0)
        gaps.append((pos, pos + gl))
        pos += gl + rng.uniform(10, 24)
    zc = 0.1 + RIM_W / 2
    edges = [x0] + [v for g in gaps for v in g] + [L / 2]
    for i in range(0, len(edges), 2):
        a, b = edges[i], edges[i + 1]
        if b - a < 0.3:
            continue
        x = a
        while x < b - 0.05:
            w = min(rng.uniform(0.9, 1.9), b - x)
            if b - x - w < 0.5:
                w = b - x
            t = rng.uniform(0.86, 1.08)
            m.box(STONE, (w * 0.995, 0.64, RIM_W), pos=(x + w / 2, 0, zc), chamfer=0.05, tint=(t, t, t))
            m.box(STONE, (w * 0.99, 0.36, RIM_W * 0.74), pos=(x + w / 2, 0.64, zc), chamfer=0.04, tint=(t * 0.96,) * 3)
            x += w
        # 压顶 + 积雪
        m.box(STONE, (b - a, 0.12, RIM_W * 0.9), pos=((a + b) / 2, 1.0, zc), chamfer=0.03, tint=(0.95,) * 3)
        m.box(SNOW, (b - a - 0.1, 0.09, RIM_W * 0.62), pos=((a + b) / 2, 1.12, zc - 0.05), chamfer=0.035, tint=snow_tint(rng, 0.62, 0.78))
        # 压顶上的冰包 + 外沿下垂的短冰棱
        xx = a + rng.uniform(0.3, 1.2)
        while xx < b - 0.3:
            ice_blob(m, xx, 1.2, zc + rng.uniform(-0.1, 0.2), rng.uniform(0.2, 0.45), 0.12, rng.uniform(0.12, 0.25), rng, squash=0.5, sink=0.2, jitter=0.2)
            xx += rng.uniform(1.8, 4.5)
        xx = a + 0.3
        while xx < b - 0.2:
            if rng.random() < 0.6:
                icicle(m, xx, 1.0, zc + RIM_W * 0.45, rng.uniform(0.12, 0.42), rng.uniform(0.03, 0.06), rng, sides=4)
            xx += rng.uniform(0.35, 0.9)
        # 墩柱：两端 + 每 ~9 m
        piers = [a + 0.33, b - 0.33] + [a + 9 * j for j in range(1, int((b - a) // 9) + 1)]
        for px_ in piers:
            if px_ < a or px_ > b:
                continue
            t = rng.uniform(0.9, 1.06)
            m.box(STONE, (0.74, 0.30, 0.74), pos=(px_, 1.0, zc), chamfer=0.04, tint=(t,) * 3)
            m.box(BRASS, (0.80, 0.05, 0.80), pos=(px_, 0.72, zc), tint=(0.8, 0.8, 0.8)) if rng.random() < 0.4 else None
    for (a, b) in gaps:        # 缺口：塌掉的石块 + 碎冰 + 散落的书
        x = a
        while x < b:
            w = rng.uniform(0.5, 1.3)
            h = rng.uniform(0.10, 0.45)
            m.box(STONE, (min(w, b - x), h, RIM_W * rng.uniform(0.7, 1.0)), pos=(x + w / 2, 0, zc + rng.uniform(-0.1, 0.2)), chamfer=0.0,
                  yaw=rng.uniform(-0.15, 0.15), tint=(rng.uniform(0.8, 1.0),) * 3)
            x += w
        for _ in range(3):
            s = rng.uniform(0.15, 0.3)
            m.rock(STONE, (s, s * 0.8, s), (rng.uniform(a, b), 0, rng.uniform(0.25, 1.7)), seed=rng.randint(0, 99999), detail=0, yaw=rng.uniform(0, TAU))
        for _ in range(2):
            ice_shard(m, rng.uniform(a, b), rng.uniform(0.4, 1.7), rng.uniform(0.3, 0.7), rng.uniform(0.1, 0.2), rng)
        for _ in range(3):
            book(m, rng, rng.uniform(a - 0.4, b + 0.4), rng.uniform(0.0, 0.1), rng.uniform(0.3, 1.9), rng.uniform(0, TAU), rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2))


def north_set(m):
    """北侧：结冰书架墙（z = −45）+ 缺口里的倒塌书架 / 冰锥 / 书堆 + 后排断裂拱廊（z ≈ −51）+ 带高窗的后墙（z = −58）+ 残梁与吊灯。"""
    rng = random.Random(501)
    zw = -45.5
    segs = [(-53.0, -37.0, 12.0, 2.0), (-33.0, -15.0, 13.8, 2.0), (-10.5, 6.0, 10.5, 2.0), (11.0, 27.0, 14.2, 2.0), (31.0, 53.0, 11.8, 2.0)]
    for i, (xa, xb, base, amp) in enumerate(segs):
        top = lambda x, base=base, amp=amp, i=i: base + amp * (rag(x * 0.35, 77 + i, 1.0) - 0.5) * 2 - 0.05 * (abs(x - (xa + xb) / 2) - 5.0 if abs(x - (xa + xb) / 2) > 5.0 else 0.0)
        shelf_wall(m, xa, xb, zw, top, 800 + i * 11)
    # 缺口里：倒塌的书架 + 冰锥 + 书堆
    for i, (gx, gw) in enumerate([(-35.0, 3.4), (-12.75, 4.0), (8.5, 4.6), (29.0, 3.4)]):
        for j in range(2):
            toppled_shelf(m, gx + rng.uniform(-gw / 2, gw / 2), zw + 1.8 + 1.8 * j, rng.uniform(-0.3, 0.3) + (math.pi / 2 if j else 0), 1.0 + rng.uniform(-0.15, 0.2), 900 + i * 7 + j, h=rng.uniform(3.4, 4.6))
        book_heap(m, gx, zw + 2.5, 2.4, 40, 1.1, 950 + i)
        for _ in range(6):
            ice_shard(m, gx + rng.uniform(-gw, gw), zw + rng.uniform(0.3, 3.5), rng.uniform(1.2, 3.2), rng.uniform(0.3, 0.6), rng)
    # 前沿书堆 / 冰锥 / 雪堆 / 阅读台（z ≈ −42..−44）
    for i, (x, z, rad, n, hm) in enumerate([(-44, -42.6, 2.6, 46, 1.2), (-27, -42.4, 2.2, 36, 1.0), (-4, -42.5, 2.4, 40, 1.0), (16, -42.4, 2.4, 40, 1.1), (36, -42.6, 2.6, 44, 1.2), (49, -43.0, 2.4, 36, 1.0)]):
        book_heap(m, x, z, rad, n, hm, 1000 + i)
    for i, (x, z, h, rx) in enumerate([(-39, -43.0, 0.9, 3.4), (-20, -42.8, 1.0, 3.0), (2, -43.4, 1.1, 3.6), (22, -43.0, 0.9, 3.2), (42, -43.2, 1.0, 3.6)]):
        drift(m, x, z, rx, 1.6, h, rng)
    for i, (x, z, yw) in enumerate([(-30, -43.6, 0.15), (-7, -43.8, -0.2), (24, -43.7, 0.1), (39, -43.9, -0.1)]):
        reading_desk(m, x, z, yw, 1100 + i)
    for _ in range(26):
        x = rng.uniform(-52, 52)
        ice_shard(m, x, rng.uniform(-43.5, -41.9), rng.uniform(0.5, 1.4), rng.uniform(0.16, 0.34), rng)
    # 后排：断裂拱廊
    zp = -51.5
    px_list = [-47, -35, -23, -11, 1, 13, 25, 37, 49]
    ph = [13.0, 16.0, 11.0, 17.0, 12.0, 15.0, 10.5, 16.5, 12.0]
    kinds = [True, False, True, False, True, True, False, True, False]            # True = 完整（带柱头）
    for x, h, full in zip(px_list, ph, kinds):
        pier(m, x + rng.uniform(-0.3, 0.3), zp + rng.uniform(-0.4, 0.4), 0.9, h, abs(int(x)) * 3 + 11, broken=not full)
    for (a, b, ka, kb) in [(-47, -35, 1.0, 0.6), (-23, -11, 1.0, 1.0), (1, 13, 0.7, 1.0), (25, 37, 1.0, 0.45), (-35, -23, 0.4, 0.0)]:
        round_arch(m, a + 0.9, b - 0.9, 9.4 if a > -40 else 8.6, zp, 1.5, 1.1, abs(int(a)) * 5 + 3, ka, kb)
    # 后墙 + 高窗
    zb = -58.0
    lan = [C.pointed_hole(cx, 6.0, 1.5, 3.4, 4.6) for cx in (-26.0, -9.0, 8.0, 26.0)]
    hole = lambda x: next((r for r in (f(x) for f in lan) if r), None)
    top = lambda x: max(13.0, 19.2 - 0.02 * x * x * 0.4) - rag(x, 5, 3.4)
    back_wall(m, -54.0, 54.0, zb, 2.0, top, hole, 77)
    for cx in (-26.0, -9.0, 8.0, 26.0):
        window_panes(m, cx, 6.0, 1.5, 3.4, 4.6, zb + 1.1, int(cx) + 100)
    # 残梁 + 吊灯
    beams = [(-24.0, 12.2, 2.0, 5.6), (-5.0, 13.0, 2.2, 5.0), (15.0, 12.4, 2.0, 6.0), (34.0, 11.6, 2.2, 5.2), (-42.0, 11.0, 1.8, 4.6)]
    for i, (bx, by, bl, drop) in enumerate(beams):
        ex, ey, ez = beam_out(m, bx, by, zw + 0.4, bl, rng)
        chandelier(m, ex, ey - drop, ez - 0.2, rng.uniform(1.1, 1.5), rng, tilt=rng.uniform(-0.12, 0.12) + (0.38 if i in (1, 3) else 0.0), roll=rng.uniform(-0.2, 0.2),
                   yaw=rng.uniform(0, TAU), chain_from=(ex, ey, ez))
    # 坠落的吊灯（躺在地上，半埋在雪里）
    for (cx, cz) in [(21.0, -43.0), (-15.0, -43.4)]:
        tmp = Mesh(31)
        chandelier(tmp, 0, 0, 0, 1.3, rng, tilt=0.75, roll=0.3)
        if grounded(tmp, (cx, cz), m, dy=0.0):
            drift(m, cx + 0.4, cz + 0.4, 2.2, 1.4, 0.55, rng)


def back_wall(m, x0, x1, z, thick, top_fn, hole_fn, seed, strip=2.0):
    """北侧后墙（几乎只在俯视整体图里看得到）：每 2 m 一条的整块石柱，顶部参差，窗洞处分成上下两段。比 C.wall_strips 的逐层砌块省 90% 三角面。"""
    rng = random.Random(seed)
    n = max(1, int(round((x1 - x0) / strip)))
    w = (x1 - x0) / n
    for i in range(n):
        xc = x0 + (i + 0.5) * w
        top = top_fn(xc)
        hole = hole_fn(xc) if hole_fn else None
        pieces = [(0.0, top)]
        if hole and hole[0] < top:
            pieces = [(0.0, hole[0])] + ([(hole[1], top)] if hole[1] < top - 0.2 else [])
        for (ya, yb) in pieces:
            t = rng.uniform(0.84, 1.08)
            m.box(STONE, (w * 0.998, yb - ya, thick * rng.uniform(0.94, 1.0)), pos=(xc, ya, z + rng.uniform(-0.05, 0.08)), chamfer=0.1 if yb == top else 0.0,
                  bottom=(ya > 0), tint=(t, t, t))


def window_panes(m, cx, y0, half_w, rise, spring, z, seed, panes=3):
    """窄尖拱窗里的发光玻璃（冷白蓝；竖向分格，部分缺失，留铅条缝）。"""
    rng = random.Random(seed)
    cols = np.linspace(cx - half_w * 0.82, cx + half_w * 0.82, panes + 1)
    for i in range(panes):
        xa, xb = cols[i], cols[i + 1]
        xm = (xa + xb) / 2
        c = abs(xm - cx) / half_w
        top = y0 + spring + rise * math.sqrt(max(0.0, 1 - c ** 1.8)) - 0.4
        rows = max(2, int((top - y0 - 0.2) / 1.6))
        ys = np.linspace(y0 + 0.2, top, rows + 1)
        for j in range(rows):
            if rng.random() < 0.20:
                continue
            m.poly(PANE, [(xa + 0.06, ys[j] + 0.05, z), (xb - 0.06, ys[j] + 0.05, z), (xb - 0.06, ys[j + 1] - 0.05, z), (xa + 0.06, ys[j + 1] - 0.05, z)])


def shelf_row_ew(m, sgn, x_in, x_out, z, top_base, seed, amp=2.0):
    """东 / 西侧的一排横向书架（沿 x，面朝南，才看得见书面）；x_in 靠近场地，x_out 远离。"""
    xa, xb = (x_in, x_out) if sgn > 0 else (-x_out, -x_in)
    top = lambda x: top_base + amp * (rag(x * 0.4, seed, 1.0) - 0.5) * 2
    shelf_wall(m, xa, xb, z, top, seed, bay=2.6, ice_k=0.6, board_ice_below=8.0)


def side_set(m, sgn, seed):
    """东（sgn=+1）/ 西（sgn=−1）：横向书架排、倾倒的书架、书堆、阅读台、雪堆、冰锥。全部在 |x| ≥ 46、|z| ≤ 40。"""
    rng = random.Random(seed)
    xin, xout = 47.2, 64.0
    rows = [(-33.0, 9.0), (-14.0, 11.5), (6.0, 8.0), (25.0, 10.0)] if sgn > 0 else [(-31.0, 10.5), (-11.0, 8.5), (9.0, 11.0), (28.0, 7.5)]
    for i, (z, h) in enumerate(rows):
        a = xin + rng.uniform(0.0, 2.4)
        b = xout - rng.uniform(0.0, 3.0)
        shelf_row_ew(m, sgn, a, b, z, h, seed * 10 + i)
        if i % 2 == 0:            # 排与排之间的横梁 / 残拱
            pass
    # 倾倒的书架 / 阅读台 / 书堆 / 雪堆（行与行之间的过道里）
    aisles = [-41.0, -24.0, -4.0, 16.0, 33.0] if sgn > 0 else [-39.0, -21.0, -1.0, 19.0, 33.0]
    for i, z in enumerate(aisles):
        zz = z
        toppled_shelf(m, sgn * rng.uniform(51.0, 55.0), zz + rng.uniform(-1, 1), rng.uniform(0, math.pi), rng.uniform(0.8, 1.25), seed * 20 + i, h=rng.uniform(3.2, 4.6))
        book_heap(m, sgn * rng.uniform(55.5, 59.5), zz + rng.uniform(-1, 1), rng.uniform(1.8, 2.8), rng.randint(36, 56), rng.uniform(0.9, 1.5), seed * 30 + i)
        reading_desk(m, sgn * rng.uniform(51.5, 58.5), zz + rng.uniform(-2, 2), rng.uniform(-0.4, 0.4), seed * 40 + i)
        drift(m, sgn * rng.uniform(51.5, 58.0), zz + rng.uniform(-1.4, 1.4), rng.uniform(2.2, 3.4), rng.uniform(1.3, 2.2), rng.uniform(0.8, 1.7), rng)
        for _ in range(4):
            ice_shard(m, sgn * rng.uniform(46.5, 62), zz + rng.uniform(-3, 3), rng.uniform(0.8, 2.4), rng.uniform(0.2, 0.5), rng)
    for z in np.linspace(-38, 38, 9):             # 护栏旁的一排矮书堆 / 雪
        book_heap(m, sgn * rng.uniform(46.2, 47.4), z + rng.uniform(-1.5, 1.5), rng.uniform(1.0, 1.6), 22, 0.8, seed * 50 + int(z), ymax=1.4)
        drift(m, sgn * rng.uniform(46.5, 47.3), z + rng.uniform(-1.5, 1.5), 1.6, 1.1, 0.8, rng, ymax=1.3, detail=0)


def south_set(m, seed=801):
    """南侧（靠近镜头）：只放低矮的东西（≤ 2 m）：成簇的小雪堆、矮书堆、平躺的书架残件、碎冰、冰锥簇、缩小的阅读台。"""
    rng = random.Random(seed)
    for i in range(17):                                   # 雪脊：每处 2–4 个重叠的小雪堆
        cx, cz = -64 + i * 7.8 + rng.uniform(-2, 2), rng.uniform(45.0, 52.0)
        for _ in range(rng.randint(2, 4)):
            drift(m, cx + rng.uniform(-2.4, 2.4), cz + rng.uniform(-1.0, 1.0), rng.uniform(1.3, 3.0), rng.uniform(0.9, 1.7), rng.uniform(0.5, 1.5), rng, ymax=1.8)
    for i, x in enumerate(np.linspace(-48, 48, 15)):      # 矮书堆
        book_heap(m, x + rng.uniform(-1.5, 1.5), 43.4 + rng.uniform(0, 2.4), rng.uniform(1.2, 2.0), rng.randint(22, 36), 0.9, seed + 10 + i, ymax=1.5)
    for i in range(7):                                    # 平躺的书架残件（≤ 1.9 m）
        toppled_shelf(m, rng.uniform(-52, 52), rng.uniform(46.5, 52.0), rng.uniform(0, math.pi), rng.uniform(1.35, 1.5), seed + 60 + i, h=rng.uniform(3.2, 4.4), ymax=1.9)
    for i in range(10):                                   # 冰锥簇
        cx, cz = rng.uniform(-60, 60), rng.uniform(43.5, 54)
        for _ in range(rng.randint(3, 6)):
            ice_shard(m, cx + rng.uniform(-1.2, 1.2), cz + rng.uniform(-1.0, 1.0), rng.uniform(0.5, 1.7), rng.uniform(0.16, 0.42), rng)
    for i, x in enumerate((-40, -17, 6, 29, 52)):
        reading_desk(m, x + rng.uniform(-1.5, 1.5), 46.4 + rng.uniform(0, 1.5), rng.uniform(-0.5, 0.5), seed + 40 + i, ymax=1.8)
    for i in range(26):
        x, z = rng.uniform(-62, 62), rng.uniform(43.5, 56)
        s_ = rng.uniform(0.2, 0.6)
        ice_blob(m, x, 0.0, z, s_, s_ * 0.9, s_ * rng.uniform(0.8, 1.2), rng)


def scatter_outer(meshes):
    """边界外一圈的碎冰 / 书（地面起伏、不显得空）：按位置丢进对应的网格。"""
    rng = random.Random(901)

    def accept(x, z):
        return abs(x) >= PLAY_X + 2.0 or abs(z) >= PLAY_Z + 2.0
    pts = poisson(rng, 150, accept, 3.6, (-66, 66, -62, 58))
    for i, (x, z) in enumerate(pts):
        if z > PLAY_Z + 1.5 and abs(x) < PLAY_X + 1.5:
            m = meshes["S"]
        elif z < -PLAY_Z - 1.5 and abs(x) < PLAY_X + 1.5:
            m = meshes["N"]
        elif x > 0:
            m = meshes["E"]
        else:
            m = meshes["W"]
        if rng.random() < 0.55:
            s = rng.uniform(0.12, 0.38)
            ice_blob(m, x, 0.0, z, s, s * 0.8, s * rng.uniform(0.8, 1.3), rng)
        else:
            book(m, rng, x, 0.0, z, rng.uniform(0, TAU), rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2))


def snow_field(m, cx, cz, rx, rz, rng, seed, y=0.035, seg=36):
    """边界外的一片薄雪（不规则多边形，贴地）。雪只放在边界外。"""
    r = random.Random(seed)
    ph = [r.uniform(0, TAU) for _ in range(3)]
    pts = []
    for k in range(seg):
        a = TAU * k / seg
        f = 1.0 + 0.22 * math.sin(3 * a + ph[0]) + 0.12 * math.sin(5 * a + ph[1]) + 0.07 * math.sin(9 * a + ph[2])
        pts.append((cx + rx * f * math.cos(a), y, cz + rz * f * math.sin(a)))
    P = np.array(pts)
    m.quad_up(SNOW, [tuple(p) for p in P], tint=snow_tint(rng, 0.72, 0.9))


def build_bounds():
    meshes = {"N": Mesh(21), "E": Mesh(22), "W": Mesh(23), "S": Mesh(24)}
    L_ns, L_ew = 2 * (PLAY_X + 0.1 + RIM_W), 2 * (PLAY_Z + 0.1)
    with meshes["N"].at((0, 0, -PLAY_Z), math.pi):
        parapet(meshes["N"], L_ns, 11)
    with meshes["S"].at((0, 0, PLAY_Z), 0.0):
        parapet(meshes["S"], L_ns, 12)
    with meshes["E"].at((PLAY_X, 0, 0), math.pi / 2):
        parapet(meshes["E"], L_ew, 13)
    with meshes["W"].at((-PLAY_X, 0, 0), -math.pi / 2):
        parapet(meshes["W"], L_ew, 14)
    north_set(meshes["N"])
    side_set(meshes["E"], +1, 3)
    side_set(meshes["W"], -1, 4)
    south_set(meshes["S"])
    scatter_outer(meshes)
    rng = random.Random(33)
    for i in range(7):                    # 边界外的薄雪片（北 / 南）
        snow_field(meshes["N"], -50 + i * 17 + rng.uniform(-4, 4), -47.5 + rng.uniform(-2, 2), rng.uniform(5, 9), rng.uniform(2.0, 3.2), rng, 60 + i)
        snow_field(meshes["S"], -50 + i * 17 + rng.uniform(-4, 4), 48.5 + rng.uniform(-2, 2), rng.uniform(5, 9), rng.uniform(2.4, 3.6), rng, 70 + i)
    parts = []
    for key, name in (("N", "BOUNDS_NORTH"), ("E", "BOUNDS_EAST"), ("W", "BOUNDS_WEST"), ("S", "BOUNDS_SOUTH")):
        sd = {"N": 1, "E": 2, "W": 3, "S": 4}[key]
        paint_mats(meshes[key], C.weathered_paint(sd, dirt_h=2.8, dirt=0.75, moss=False), (STONE, WOOD, BOOKS))
        paint_mats(meshes[key], lambda P, sd=sd: (0.84 + 0.30 * vnoise(P, 0.35, sd + 20) + 0.10 * vnoise(P, 1.3, sd + 30))[:, None] * np.ones((1, 3)), (SNOW,))
        parts.append(Part(name, "ARENA_BOUNDS", meshes[key]))
    if os.environ.get("ARENA_AO", "1") != "0":
        C.bake_ao(list(meshes.values()), skip_mats=(PANE,), strength=0.52)
    return parts


# =====================================================================
# 场内道具（ARENA_PROPS）：低矮（≤ 0.6 m）、稀疏、中心 18 m 半径内保持干净
# =====================================================================
def frost_crack(m, x, z, rng, length):
    """冰裂缝贴片：随机折线 + 分叉，浅灰蓝的窄带贴地（y = 0.016）；走到场外 / 中心空地就截断。"""
    def inside(px, pz):
        return abs(px) < PLAY_X - 0.9 and abs(pz) < PLAY_Z - 0.9 and math.hypot(px, pz) > CLEAN_R + 0.4

    ang = rng.uniform(0, TAU)
    pts, widths = [(x, z)], [0.04]
    px, pz = x, z
    n = max(4, int(length / 0.9))
    for k in range(n):
        ang += rng.uniform(-0.55, 0.55)
        qx, qz = px + math.cos(ang) * length / n, pz + math.sin(ang) * length / n
        if not inside(qx, qz):
            break
        px, pz = qx, qz
        pts.append((px, pz))
        widths.append(rng.uniform(0.03, 0.09) * (1.0 - 0.6 * k / n))
    if len(pts) < 3:
        return
    tint = (0.42, 0.50, 0.60)
    m.strip_xz(SNOW, pts, widths, y=0.016, tint=tint)
    if len(pts) >= 5 and rng.random() < 0.8:
        k0 = rng.randint(2, len(pts) - 2)
        bx, bz = pts[k0]
        a2 = ang + rng.choice((-1, 1)) * rng.uniform(0.5, 1.0)
        bp, bw = [(bx, bz)], [widths[k0] * 0.8]
        for k in range(3):
            qx, qz = bx + math.cos(a2) * length / n * 0.9, bz + math.sin(a2) * length / n * 0.9
            if not inside(qx, qz):
                break
            bx, bz = qx, qz
            a2 += rng.uniform(-0.4, 0.4)
            bp.append((bx, bz))
            bw.append(max(0.025, bw[-1] * 0.7))
        if len(bp) >= 2:
            m.strip_xz(SNOW, bp, bw, y=0.016, tint=tint)


def snow_patch(m, x, z, rng, size):
    """小雪片贴片（灰蓝、很薄；不是大面积的白）。"""
    seg = 12
    ph = rng.uniform(0, TAU)
    pts = []
    for k in range(seg):
        a = TAU * k / seg
        f = 1.0 + 0.30 * math.sin(2 * a + ph) + 0.15 * math.sin(4 * a + 2 * ph)
        pts.append((x + size * f * math.cos(a), 0.013, z + size * 0.7 * f * math.sin(a)))
    t = rng.uniform(0.5, 0.68)
    m.quad_up(SNOW, pts, tint=(t, t * 1.04, t * 1.12))


def scroll(m, x, z, rng):
    """卷轴筒：横躺的细圆柱 + 两端黄铜帽。最高约 0.14 m。"""
    ln, r = rng.uniform(0.45, 0.8), rng.uniform(0.035, 0.05)
    with m.at((x, r + 0.01, z), rng.uniform(0, TAU), math.pi / 2):
        m.lathe(SNOW, [(r, -ln / 2), (r, ln / 2)], 6, smooth=True, share=True, cap_bottom=True, cap_top=True, tint=(0.62, 0.56, 0.46))
        for s_ in (-1, 1):
            m.lathe(BRASS, [(r * 1.18, s_ * ln / 2 - 0.02), (r * 1.18, s_ * ln / 2 + 0.02)], 6, smooth=True, share=True, cap_bottom=True, cap_top=True)


def build_props():
    """ARENA_PROPS：散落的书、卷轴筒、碎冰块、散页、小雪片、冰裂缝。全部在可活动区域里、≤ 0.6 m、离中心 ≥ 18 m。"""
    m = Mesh(41)
    rng = random.Random(41)
    R0 = CLEAN_R + 1.0

    def ok(x, z):
        r = math.hypot(x, z)
        if abs(x) > PLAY_X - 1.2 or abs(z) > PLAY_Z - 1.2 or r < R0:
            return False
        return rng.random() < 0.18 + 0.82 * float(T.smoothstep(20.0, 44.0, r))

    box = (-PLAY_X, PLAY_X, -PLAY_Z, PLAY_Z)
    for (x, z) in poisson(rng, 46, ok, 6.5, box):                              # 散落的书（2–4 本一簇）
        for _ in range(rng.randint(2, 4)):
            a, d = rng.uniform(0, TAU), rng.uniform(0.0, 0.7)
            book(m, rng, x + d * math.cos(a), 0.0, z + d * math.sin(a), rng.uniform(0, TAU), rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15))
        if rng.random() < 0.5:
            page(m, rng, x + rng.uniform(-0.8, 0.8), z + rng.uniform(-0.8, 0.8))
    for (x, z) in poisson(rng, 40, ok, 5.5, box):                              # 碎冰块
        s0 = rng.uniform(0.12, 0.28)
        ice_blob(m, x, 0.0, z, s0, s0 * 0.8, s0 * rng.uniform(0.8, 1.25), rng, tint=ice_tint(rng, 0.7, 0.95))
        for _ in range(rng.randint(1, 3)):
            a, d = rng.uniform(0, TAU), rng.uniform(0.25, 0.8)
            s1 = rng.uniform(0.05, 0.14)
            ice_blob(m, x + d * math.cos(a), 0.0, z + d * math.sin(a), s1, s1 * 0.8, s1, rng, tint=ice_tint(rng, 0.7, 0.95))
    for (x, z) in poisson(rng, 16, ok, 9.0, box):                              # 卷轴筒
        scroll(m, x, z, rng)
    for (x, z) in poisson(rng, 26, ok, 6.0, box):                              # 散页
        for _ in range(rng.randint(2, 4)):
            page(m, rng, x + rng.uniform(-0.7, 0.7), z + rng.uniform(-0.7, 0.7))
    for (x, z) in poisson(rng, 24, ok, 6.5, box):                              # 小雪片
        snow_patch(m, x, z, rng, rng.uniform(0.35, 0.8))
    for (x, z) in poisson(rng, 14, ok, 11.0, box):                             # 冰裂缝
        frost_crack(m, x, z, rng, rng.uniform(3.0, 8.5))
    if os.environ.get("ARENA_AO", "1") != "0":
        C.bake_ao([m], skip_mats=(SNOW,), samples=10, dist=1.2, strength=0.5)
    return [Part("PROPS_FLOOR_SCATTER", "ARENA_PROPS", m)]


# =====================================================================
# 北窗光柱（ARENA_LIGHTS）：半透明冷白蓝体积光片，从北侧高窗斜射向场内；透明度沿长度 / 宽度渐隐（顶点色 A）
# =====================================================================
SHAFTS = [  # (材质, 窗口 x, 窗口 z, 窗口顶高, 落点 x, 落点 z, 顶宽, 底宽)
    (SHAFT, -26.0, -53.0, 14.5, -21.0, -30.0, 2.8, 4.4),
    (SHAFT, -9.0, -54.0, 15.0, -6.0, -26.0, 2.6, 4.0),
    (SHAFT, 26.0, -53.0, 14.0, 30.0, -31.0, 2.6, 4.0),
]


def shaft_mesh(spec, seed):
    mat, xw, zw, yw, xl, zl, w0, w1 = spec
    m = Mesh(seed)
    T0 = np.array([xw, yw, zw])
    B = np.array([xl, 0.03, zl])
    rows, cols = 9, 5
    prof = np.array([0.10, 0.55, 1.0, 0.55, 0.10])
    P, A = [], []
    for i in range(rows + 1):
        t = i / rows
        c = T0 + (B - T0) * t
        w = w0 + (w1 - w0) * t
        fade = float(T.smoothstep(0.0, 0.22, t) * (1.0 - T.smoothstep(0.58, 1.0, t)))
        for j in range(cols):
            u = (j / (cols - 1) - 0.5)
            P.append((c[0] + u * w, c[1], c[2]))
            A.append(prof[j] * fade)
    F = []
    for i in range(rows):
        for j in range(cols - 1):
            a = i * cols + j
            F.append([a, a + 1, a + cols + 1, a + cols])
    m.add(np.array(P), F, mat, False, tint=(1, 1, 1), alpha=np.array(A))
    d = B - T0
    d[1] = 0.0
    d /= np.linalg.norm(d)
    side = np.array([1.0, 0.0, 0.0])
    L, Wd = 7.5, w1 * 1.15
    pp, aa = [], []
    for gi in range(3):
        for gj in range(3):
            fl, fw = (gi - 1), (gj - 1)
            pp.append(tuple(B + d * fl * L * 0.5 + side * fw * Wd * 0.5 + np.array([0, 0.012, 0])))
            aa.append(1.0 if (gi == 1 and gj == 1) else 0.0)
    FF = []
    for gi in range(2):
        for gj in range(2):
            a = gi * 3 + gj
            FF.append([a, a + 1, a + 4, a + 3])
    m.add(np.array(pp), FF, mat, False, tint=(1, 1, 1), alpha=np.array(aa) * 0.55)
    return m


def build_lights():
    return [Part(f"LIGHT_SHAFT_{i}", "ARENA_LIGHTS", shaft_mesh(sp, 900 + i)) for i, sp in enumerate(SHAFTS)]


def build():
    parts = []
    for name, fn in (("floor", build_floor), ("bounds", build_bounds), ("props", build_props), ("lights", build_lights)):
        if name in PARTS:
            parts += fn()
    return parts
