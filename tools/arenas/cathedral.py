"""琉璃大教堂（区域 0）· 场地配方。

接口（build_arena.py 调用）：MOOD / make_specs(texdir) / build() → [Part...]。
通用部分在 common.py（网格构建器 / 材质 / 装配 / 导出 / 散布），贴图配方在 cathedral_tex.py。
给其余三个区域复用时：保留本文件的“结构”——四个构建函数 + 材质表 + 布局表——换掉里面的造型与配色。

布局（游戏坐标，+X 东 / +Z 南 / −Z 北；屏幕上方 = 北）：
  可活动区域 |x| ≤ 44、|z| ≤ 40；边界基座 / 栏杆内侧贴着边界线（|x| = 44.1、|z| = 40.1）。
  北侧（离镜头最远，最能入镜）：三排断柱 + 尖拱，后面是带玫瑰窗的残墙，东北 / 西北各一座高大的角墩；
  东西两侧：两排断柱（局部有尖拱）、倾倒的长椅堆、碎石；
  南侧（靠近镜头）：全部 ≤ 2 m。
"""

import math
import os
import random

import numpy as np

from arenas import cathedral_tex as CT
from arenas import textures as T
from arenas import common as C
from arenas.common import (CLEAN_R, FLOOR_X, FLOOR_Z, PLAY_X, PLAY_Z, MatSpec, Mesh, Part, clear_of_play, lin, poisson, rag,
                           vnoise)

ID = "cathedral"
TITLE = "Glass Cathedral"
MOOD = "#70bdca"
EMBLEM_CENTER = (0.0, 0.0)

FLOOR = "Arena Floor Mosaic"
EMBLEM = "Arena Emblem Mosaic"
STONE = "Arena Stone"
BRASS = "Arena Brass"
WOOD = "Arena Wood"
SHARD = "Arena Glass Shard"
WIN_C = "Arena Window Cyan"
WIN_R = "Arena Window Rose"
FLAME = "Arena Candle Flame"
SHAFT_C = "Arena Shaft Cyan"
SHAFT_R = "Arena Shaft Rose"
CIRCUIT = "Arena Circuit Trace"

EDGE_X, EDGE_Z = PLAY_X + 0.1, PLAY_Z + 0.1       # 边界基座内侧
RIM_W = 1.3                                        # 基座宽度
TAU = math.tau
PARTS = os.environ.get("ARENA_PARTS", "floor,bounds,props,lights").split(",")


# =====================================================================
# 材质与贴图
# =====================================================================
def _down2(a):
    """2×2 平均缩小（法线要重新归一）。"""
    n = a.shape[0] // 2
    return a.reshape(n, 2, n, 2, -1).astype(np.float64).mean(axis=(1, 3))


def make_specs(texdir):
    """生成贴图并返回 {材质名: MatSpec}。"""
    fl = CT.make_floor()
    emb = CT.make_emblem()
    st = CT.make_stone()
    sizes = {}

    def put(name, arr):
        p = texdir / name
        sizes[name] = T.write_png(p, arr)
        return p

    en = _down2(emb["normal"] / 255.0 * 2 - 1)
    en = en / np.linalg.norm(en, axis=-1, keepdims=True)
    emb_normal = T.to_u8(en * 0.5 + 0.5)
    emb_em = T.to_u8(_down2(emb["emissive"] / 255.0)[..., :3])
    tex = dict(
        floor=dict(base=put("floor_base.png", fl["base"]), normal=put("floor_normal.png", fl["normal"]),
                   mr=put("floor_mr.png", fl["mr"])),
        emblem=dict(base=put("emblem_base.png", emb["base"]), normal=put("emblem_normal.png", emb_normal),
                    emissive=put("emblem_emissive.png", emb_em)),
        stone=dict(base=put("stone_base.png", st["base"]), normal=put("stone_normal.png", st["normal"])),
    )
    print("TEXTURES", {k: f"{v / 1024:.0f}KB" for k, v in sizes.items()}, "circuit paths", fl["stats"])
    return {
        FLOOR: MatSpec(FLOOR, tex=tex["floor"], uv="floor", uv_scale=CT.TILE_M, normal_strength=1.0),
        EMBLEM: MatSpec(EMBLEM, tex=tex["emblem"], strength=0.6, rough=0.42, metal=0.12, uv="floor", uv_scale=2 * CT.EMBLEM_R,
                        uv_offset=(0.5, 0.5), normal_strength=1.0),
        STONE: MatSpec(STONE, tex=tex["stone"], rough=0.88, uv="box", uv_scale=CT.STONE_M, normal_strength=1.0),
        BRASS: MatSpec(BRASS, base="#8c6f3a", metal=0.85, rough=0.42),
        WOOD: MatSpec(WOOD, base="#5a4332", rough=0.8),
        SHARD: MatSpec(SHARD, base="#9fd6e0", rough=0.10, double=True),
        WIN_C: MatSpec(WIN_C, base="#0c2a31", emit="#2fa6c2", strength=0.85, double=True, rough=0.3),
        WIN_R: MatSpec(WIN_R, base="#2a1020", emit="#c0508a", strength=0.85, double=True, rough=0.3),
        CIRCUIT: MatSpec(CIRCUIT, base="#000000", emit="#45b0c6", strength=0.75, rough=1.0),
        FLAME: MatSpec(FLAME, base="#3a2810", emit="#ffb25a", strength=2.2, double=True),
        # 光柱：半透明、双面、发光已按透明度预乘（目标亮度 × alpha）；透明度的渐隐由顶点色 A 给出
        SHAFT_C: MatSpec(SHAFT_C, base="#000000", emit="#4cb6d2", strength=round(1.9 * 0.42, 3), alpha=0.42, vcolor_alpha=True, rough=1.0),
        SHAFT_R: MatSpec(SHAFT_R, base="#000000", emit="#e0629a", strength=round(1.8 * 0.38, 3), alpha=0.38, vcolor_alpha=True, rough=1.0),
    }


# =====================================================================
# 通用小件
# =====================================================================
# 通用造景件（common.py）套上本区域的材质名
def stone_paint(seed=0):
    return C.weathered_paint(seed)


def rubble_heap(m, x, z, radius, n, hmax, seed, ymax=None):
    C.rubble_heap(m, STONE, x, z, radius, n, hmax, seed, ymax)


def wall_strips(m, x0, x1, z, thick, top_fn, hole_fn, seed, strip=0.75):
    C.wall_strips(m, STONE, x0, x1, z, thick, top_fn, hole_fn, seed, strip)


def steps(m, x0, x1, z, depth, tiers, seed):
    C.steps(m, STONE, x0, x1, z, depth, tiers, seed)


pointed_hole, round_hole = C.pointed_hole, C.round_hole


def column(m, r, h, seed, capital=False, broken=True, flutes=8, base=True):
    """哥特圆柱：方柱础 + 圆环 + 凹槽鼓石叠柱 + 柱头（capital=True）或锯齿断口（broken=True）。局部原点 = 柱底中心。
    返回柱顶高度（柱头顶面 / 断口平均高）。"""
    rng = random.Random(seed)
    y = 0.0
    if base:
        m.stack_rect(STONE, r * 1.55, r * 1.55, [(0, 0), (0, 0.34), (r * 0.10, 0.42)], bottom=False)
        m.lathe(STONE, [(r * 1.30, 0.42), (r * 1.34, 0.52), (r * 1.18, 0.66), (r * 1.04, 0.74)], 16, smooth=True, share=True,
                cap_bottom=False, cap_top=False)
        y = 0.74
    top_y = h - (1.25 if capital else 0.0)
    nd = max(1, int(round((top_y - y) / 2.3)))
    dh = (top_y - y) / nd
    for i in range(nd):
        ra = r * (1.0 - 0.07 * (y - 0.74) / max(h, 1.0))
        rb = r * (1.0 - 0.07 * (y + dh - 0.74) / max(h, 1.0))
        last = i == nd - 1
        jag = (min(0.9 * r + 0.25, 0.85 * dh), seed * 7 + i) if (last and broken and not capital) else None
        tt = rng.uniform(0.9, 1.08)
        m.lathe(STONE, [(ra, y), (rb, y + dh)], flutes * 2, smooth=False, rmod=[1.0, 0.92],
                cap_bottom=False, cap_top=bool(jag), top_jag=jag, tint=(tt, tt, tt))
        y += dh
        if not last:            # 鼓石接缝处一圈线脚，盖住接缝
            m.lathe(STONE, [(rb * 1.045, y - 0.05), (rb * 1.045, y + 0.05)], flutes * 2, smooth=False,
                    cap_bottom=False, cap_top=False, tint=(0.92, 0.92, 0.92))
    if capital:
        m.lathe(STONE, [(r * 0.93, y), (r * 1.00, y + 0.20), (r * 1.22, y + 0.52), (r * 1.52, y + 0.88)], 16, smooth=True, share=True,
                cap_bottom=False, cap_top=False)
        m.stack_rect(STONE, r * 1.68, r * 1.68, [(0, y + 0.88), (0, y + 1.15), (r * 0.10, y + 1.25)], bottom=False)
        y += 1.25
    return y


def _arc_block(m, mat, c, th0, th1, r0, r1, z0, z1, tint, end_lo=False, end_hi=False, wreck=None):
    """拱圈上的一块：圆心 c、弧度 th0..th1、半径 r0..r1、进深 z0..z1。只出外露的 4 个面（内圈 / 外圈 / 前 / 后），
    起拱端和断口端才补端面；wreck = (rng, 幅度) 把末端顶点打乱（断口）。"""
    cx, cy = c

    def pt(t, rad, z):
        return np.array([cx + rad * math.cos(t), cy + rad * math.sin(t), z])
    V = np.array([pt(th0, r0, z0), pt(th1, r0, z0), pt(th1, r1, z0), pt(th0, r1, z0),
                  pt(th0, r0, z1), pt(th1, r0, z1), pt(th1, r1, z1), pt(th0, r1, z1)])
    if wreck:
        rng, amp = wreck
        for j in (1, 2, 5, 6):
            V[j] += rng.uniform(-amp, amp, 3) * np.array([1, 1, 0.5])
    F = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [3, 2, 6, 7]]
    if end_lo:
        F.append([0, 3, 7, 4])
    if end_hi:
        F.append([1, 2, 6, 5])
    m.solid(mat, V, F, ref=V.mean(axis=0), tint=tint)


def pointed_arch(m, xa, xb, y0, depth, thick, seed, n=9, keep_a=1.0, keep_b=1.0, mat=STONE):
    """等边尖拱（局部坐标：拱面在 z = 0 平面，跨 [xa, xb]，起拱高 y0，进深 depth 沿 z）。
    keep_a / keep_b：左 / 右半拱保留的比例（断拱），断口处最后一块的端面被随机打碎。外圈再套一圈薄线脚。"""
    S = xb - xa
    R = S
    rng = np.random.default_rng(seed)
    halves = [((xb, y0), math.pi, 2 * math.pi / 3, keep_a), ((xa, y0), 0.0, math.pi / 3, keep_b)]
    for (cx, cy), th0, th1, keep in halves:
        nk = int(math.ceil(n * keep - 1e-6))
        for i in range(nk):
            t0 = th0 + (th1 - th0) * i / n
            t1 = th0 + (th1 - th0) * (i + 1) / n
            tt = 0.9 + 0.18 * rng.random()
            last = (i == nk - 1 and keep < 1.0)
            _arc_block(m, mat, (cx, cy), t0, t1, R, R + thick, -depth / 2, depth / 2, (tt,) * 3,
                       end_lo=(i == 0), end_hi=last, wreck=(rng, 0.45) if last else None)
            if not last:
                _arc_block(m, mat, (cx, cy), t0, t1, R - thick * 0.38, R + 0.02, -depth / 2 - 0.12, depth / 2 + 0.12, (tt * 0.9,) * 3,
                           end_lo=(i == 0))


def fallen_drum(m, pos, yaw, r, length, seed, tilt=0.0, roll=0.0):
    """倒卧的柱鼓石（半埋）。pos 为中心的地面坐标。"""
    if not clear_of_play(pos[0], pos[1], length / 2 + r):
        return
    with m.at((pos[0], r * 0.82, pos[1]), yaw, math.pi / 2 + tilt, roll):
        m.lathe(STONE, [(r, -length / 2), (r * 0.985, length / 2)], 16, smooth=False, rmod=[1.0, 0.92], cap_bottom=True,
                cap_top=True, top_jag=(0.25 * r, seed))


def rose_window(m, cx, cy, z, Rr, seed, broken_arc=None, missing=0.28):
    """玫瑰窗残骸（拱面朝 +Z）：外框 + 12 根窗棂 + 内外两圈花窗格，格里嵌发光彩色玻璃（青 / 玫红，部分缺失）。"""
    rng = random.Random(seed)
    seg = 56
    tw, depth = 0.62, 1.15

    def inb(th):
        return broken_arc is None or not (broken_arc[0] <= (th % TAU) <= broken_arc[1])

    for i in range(seg):
        t0, t1 = i * TAU / seg, (i + 1) * TAU / seg
        if not inb((t0 + t1) / 2):
            continue
        r0, r1 = Rr - 0.15, Rr + tw
        def p(t, rad, zz):
            return (cx + rad * math.cos(t), cy + rad * math.sin(t), zz)
        V = np.array([p(t0, r0, z - depth / 2), p(t1, r0, z - depth / 2), p(t1, r1, z - depth / 2), p(t0, r1, z - depth / 2),
                      p(t0, r0, z + depth / 2), p(t1, r0, z + depth / 2), p(t1, r1, z + depth / 2), p(t0, r1, z + depth / 2)])
        F = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
        tt = rng.uniform(0.88, 1.05)
        m.solid(STONE, V, F, tint=(tt,) * 3)
    # 窗棂（12 根，径向）+ 内圈 / 轮毂圈
    hub = Rr * 0.17
    mid = Rr * 0.55
    for k in range(12):
        a = k * TAU / 12
        if not inb(a):
            continue
        with m.at((cx, cy, z), 0.0, 0.0, a):
            # 局部 x 轴 = 径向；roll 绕 z 轴
            m.box(STONE, (Rr - hub, 0.30, 0.55), pos=((Rr + hub) / 2, 0, 0), anchor="center", bottom=True)
    for rr, w in ((hub, 0.42), (mid, 0.30)):
        for i in range(32):
            t0, t1 = i * TAU / 32, (i + 1) * TAU / 32
            if not inb((t0 + t1) / 2):
                continue
            def p(t, rad, zz):
                return (cx + rad * math.cos(t), cy + rad * math.sin(t), zz)
            V = np.array([p(t0, rr - w / 2, z - 0.28), p(t1, rr - w / 2, z - 0.28), p(t1, rr + w / 2, z - 0.28), p(t0, rr + w / 2, z - 0.28),
                          p(t0, rr - w / 2, z + 0.28), p(t1, rr - w / 2, z + 0.28), p(t1, rr + w / 2, z + 0.28), p(t0, rr + w / 2, z + 0.28)])
            F = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
            m.solid(STONE, V, F, tint=(0.95,) * 3)
    # 彩色玻璃：花窗格（两排，窗棂之间），每格再分三片、片间留铅条缝（露出后面的暗处）；青为主、玫红点缀，部分缺失
    rows = [(hub + 0.22, mid - 0.2), (mid + 0.18, Rr - 0.12)]
    for k in range(12):
        t0, t1 = k * TAU / 12 + 0.09, (k + 1) * TAU / 12 - 0.09
        for ri, (r0, r1) in enumerate(rows):
            if not inb((t0 + t1) / 2) or rng.random() < missing:
                continue
            sub = 3
            for s in range(sub):
                if rng.random() < 0.10:
                    continue
                mat = WIN_R if rng.random() < 0.30 else WIN_C
                a0 = t0 + (t1 - t0) * s / sub + 0.012
                a1 = t0 + (t1 - t0) * (s + 1) / sub - 0.012
                q0, q1 = r0 + 0.05, r1 - 0.05
                P = [(cx + q0 * math.cos(a0), cy + q0 * math.sin(a0), z + 0.1), (cx + q0 * math.cos(a1), cy + q0 * math.sin(a1), z + 0.1),
                     (cx + q1 * math.cos(a1), cy + q1 * math.sin(a1), z + 0.1), (cx + q1 * math.cos(a0), cy + q1 * math.sin(a0), z + 0.1)]
                m.poly(mat, P)
    # 轮毂：一块玫红玻璃盘
    disc = [(cx + hub * 0.9 * math.cos(t), cy + hub * 0.9 * math.sin(t), z + 0.1) for t in np.linspace(0, TAU, 13)[:-1]]
    if inb(0.5):
        m.poly(WIN_R, disc)


def lancet_window_glass(m, cx, y0, half_w, rise, spring, z, seed, panes=3):
    """窄尖拱窗里的彩色玻璃（竖向分格）：x 方向分 panes 列，高度跟窗洞曲线。"""
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
            if rng.random() < 0.18:
                continue
            mat = WIN_C if (i + j) % 2 else WIN_R
            m.poly(mat, [(xa + 0.06, ys[j] + 0.05, z), (xb - 0.06, ys[j] + 0.05, z), (xb - 0.06, ys[j + 1] - 0.05, z), (xa + 0.06, ys[j + 1] - 0.05, z)])


def pew(m, length, seed, broken=False):
    """长椅（局部：长边沿 x，原点在地面中心）：座板、靠背、两端侧板、横撑。"""
    rng = random.Random(seed)
    L = length
    m.box(WOOD, (L, 0.07, 0.48), pos=(0, 0.42, 0.0), anchor="center", bottom=True)
    m.box(WOOD, (L, 0.78, 0.06), pos=(0, 0.88, -0.25), anchor="center", pitch=-0.10, bottom=True)
    for sx in (-L / 2 + 0.05, L / 2 - 0.05):
        m.box(WOOD, (0.07, 1.20, 0.62), pos=(sx, 0.0, -0.05), bottom=True, chamfer=0.03)
    m.box(WOOD, (L - 0.2, 0.06, 0.06), pos=(0, 0.14, 0.12), anchor="center")
    if broken:
        pass


def pew_pile(m, cx, cz, count, seed, spread=2.6, layers=2, ymax=None):
    """倾倒长椅堆：每张随机朝向 / 侧翻 / 倾斜，落地到刚好不穿地，再堆几层（层高 ~0.55）；ymax 限制整体高度。"""
    rng = random.Random(seed)
    for i in range(count):
        layer = min(layers - 1, int(i / max(1, count / layers)))
        x = cx + rng.uniform(-spread, spread)
        z = cz + rng.uniform(-spread, spread) * 0.8
        if not clear_of_play(x, z, 1.9):
            continue
        yaw = rng.uniform(0, math.pi)
        roll = rng.choice([0.0, 0.0, 1.5708, -1.5708, 0.7, -0.7, 2.4])
        pitch = rng.uniform(-0.25, 0.25)
        tmp = Mesh(seed * 17 + i)
        with tmp.at((0, 0, 0), yaw, pitch, roll):
            pew(tmp, rng.uniform(2.6, 3.4), seed * 31 + i)
        hmax = max(W[:, 1].max() for W in tmp.P) - tmp.min_y()
        dy = -tmp.min_y() + layer * 0.55 + rng.uniform(0.0, 0.1)
        if ymax is not None and hmax + layer * 0.55 + 0.1 > ymax:
            dy = -tmp.min_y()
            if hmax > ymax:
                continue
        m.absorb(tmp, (x, dy, z))


# =====================================================================
# 地面
# =====================================================================
# 地砖基础色是中性玻璃明度图，色相由这里的顶点色（低频、不重复）给出：按低频“场”的分位数从青 → 蓝 → 靛 → 紫 → 玫红 → 琥珀。
# 顶点色是线性乘数且只能 ≤ 1，所以用“期望的最终颜色 / 贴图中值明度”折算。
MACRO_STOPS = [(0.00, "#1b5f6b"), (0.36, "#1f6672"), (0.58, "#226071"), (0.74, "#245676"), (0.86, "#274b78"),
               (0.935, "#363f72"), (0.975, "#4a3866"), (1.00, "#5a4a30")]
TEX_REF_LUM = 0.33
CIRCUIT_TILE_WALKS = 3.6          # 每块 12 m 地砖里随机走线条数（场内）


def build_floor():
    """ARENA_FLOOR：整片地砖（3 m 网格，顶点色给色相 / 明暗 / 污渍）+ 中央玫瑰窗纹章（30 m 圆盘 + 黄铜外圈）+ 电路走线几何。"""
    m = Mesh(11)
    P = C.floor_grid(m, FLOOR, 3.0)
    # 色相场：低频噪声（~18 m）按分位数映射到色板；再叠明暗 / 污渍 / 边界外渐暗
    field = 0.62 * vnoise(P, 0.055, 31) + 0.28 * vnoise(P, 0.13, 32) + 0.10 * vnoise(P, 0.31, 33)
    pct = np.argsort(np.argsort(field)) / float(len(field) - 1)
    col = C.macro_color(pct, MACRO_STOPS, TEX_REF_LUM)
    big, mid = vnoise(P, 0.045, 5), vnoise(P, 0.16, 8)
    dirt = T.smoothstep(0.62, 0.82, vnoise(P, 0.22, 12))
    d_out = np.maximum(np.maximum(np.abs(P[:, 0]) - PLAY_X, np.abs(P[:, 2]) - PLAY_Z), 0.0)
    fade = 1.0 - 0.40 * T.smoothstep(0.0, 14.0, d_out)
    v = (0.80 + 0.30 * big + 0.12 * mid) * (1 - 0.30 * dirt) * fade
    m.C[-1][:, :3] = col * v[:, None]
    # 纹章圆盘（略高于地面 0.02，避免共面）+ 黄铜外圈（低矮倒角环）
    C.disc(m, EMBLEM, CT.EMBLEM_R, tint=(0.64, 0.66, 0.68), y=0.02)
    with m.at((0, 0.02, 0)):
        m.lathe(BRASS, [(15.0, -0.02), (15.34, -0.02), (15.34, 0.03), (15.12, 0.055), (15.0, 0.055), (15.0, -0.02)], 96,
                smooth=False, cap_bottom=False, cap_top=False)
    graph = T.VoronoiGraph(CT.FLOOR_CELLS, CT.FLOOR_JITTER, CT.FLOOR_SEED)       # 种子与地砖贴图一致 → 走线贴着铅条
    dens = lambda x, z: float(T.smoothstep(0.30, 0.62, vnoise(np.array([[x, 0.0, z]]), 0.05, 3)[0]))
    n_circ = C.circuit_ribbons(m, graph, CT.TILE_M, (CIRCUIT, WIN_R), CIRCUIT_TILE_WALKS, dens, exclude_r=CT.EMBLEM_R + 0.6)
    print(f"FLOOR circuits walks {n_circ}")
    return [Part("FLOOR_TILES", "ARENA_FLOOR", m)]


# =====================================================================
# 边界与布景（ARENA_BOUNDS）
# =====================================================================
def rim_wall(m, length, seed):
    """沿一条边的低矮基座 + 栏杆（局部：x 沿边，z 向外，内侧面在 z = 0.1）。总高 ≤ 1.46 m；随机几处缺口（断掉的栏杆 / 碎石）。"""
    rng = random.Random(seed)
    L, x0 = length, -length / 2
    gaps, pos = [], x0 + rng.uniform(5, 12)
    while pos < L / 2 - 7:
        gl = rng.uniform(1.8, 5.2)
        gaps.append((pos, pos + gl))
        pos += gl + rng.uniform(10, 24)
    zc = 0.1 + RIM_W / 2
    edges = [x0] + [v for g in gaps for v in g] + [L / 2]
    for i in range(0, len(edges), 2):
        a, b = edges[i], edges[i + 1]
        if b - a < 0.3:
            continue
        t = rng.uniform(0.9, 1.08)
        m.box(STONE, (b - a, 0.5, RIM_W), pos=((a + b) / 2, 0, zc), chamfer=0.07, tint=(t, t, t))
        m.box(STONE, (b - a, 0.2, 0.62), pos=((a + b) / 2, 1.18, zc), chamfer=0.05, tint=(t * 0.95,) * 3)
        k = 0
        x = a + 0.35
        while x < b - 0.2:
            if rng.random() > 0.035:
                tt = rng.uniform(0.9, 1.08)
                with m.at((x, 0, zc), rng.uniform(0, 1)):
                    m.lathe(STONE, [(0.058, 0.5), (0.094, 0.76), (0.062, 1.18)], 5, smooth=True, share=True,
                            cap_bottom=False, cap_top=False, tint=(tt, tt, tt))
            x += 0.66
        # 墩柱：两端 + 每 ~11 m 一个
        piers = [a + 0.31, b - 0.31] + [a + 11 * j for j in range(1, int((b - a) // 11) + 1)]
        for px_ in piers:
            if px_ < a or px_ > b:
                continue
            m.box(STONE, (0.66, 0.86, 0.66), pos=(px_, 0.5, zc), chamfer=0.0, tint=(t,) * 3)
            m.box(STONE, (0.84, 0.10, 0.84), pos=(px_, 1.36, zc), chamfer=0.03, tint=(t * 0.97,) * 3)
    for (a, b) in gaps:        # 缺口：断掉的基座块 + 碎石 + 倒下的栏杆
        x = a
        while x < b:
            w = rng.uniform(0.5, 1.3)
            h = rng.uniform(0.10, 0.42)
            m.box(STONE, (min(w, b - x), h, RIM_W * rng.uniform(0.7, 1.0)), pos=(x + w / 2, 0, zc + rng.uniform(-0.1, 0.2)), chamfer=0.0,
                  yaw=rng.uniform(-0.15, 0.15), tint=(rng.uniform(0.8, 1.0),) * 3)
            x += w
        for _ in range(3):
            s = rng.uniform(0.15, 0.3)
            m.rock(STONE, (s, s * 0.8, s), (rng.uniform(a, b), 0, rng.uniform(0.25, 1.7)), seed=rng.randint(0, 99999), detail=0,
                   yaw=rng.uniform(0, TAU))
        for _ in range(3):
            fx, fz = rng.uniform(a - 0.5, b + 0.5), rng.uniform(0.3, 1.9)
            with m.at((fx, 0.07, fz), rng.uniform(0, math.pi), math.pi / 2, 0.0):
                m.lathe(STONE, [(0.05, -0.36), (0.085, -0.1), (0.05, 0.36)], 5, smooth=True, share=True, cap_bottom=True, cap_top=True)


def place_column(m, x, z, r, h, kind, seed):
    rng = random.Random(seed)
    with m.at((x, 0, z), rng.uniform(0, TAU)):
        return column(m, r, h, seed, capital=(kind == "i"), broken=(kind == "b"))


def arch_between(m, p1, p2, y_spring, along_x, depth, thick, seed, keep_a=1.0, keep_b=1.0, n=9, inset=0.9):
    """两根柱子之间的尖拱。p1 / p2 为柱位 (x, z)；along_x=True 拱面沿 x（拱在 z 平面），否则沿 z。"""
    cx, cz = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    S = abs(p2[0] - p1[0]) if along_x else abs(p2[1] - p1[1])
    with m.at((cx, 0, cz), 0.0 if along_x else math.pi / 2):
        pointed_arch(m, -S / 2 + inset, S / 2 - inset, y_spring, depth, thick, seed, n, keep_a, keep_b)


def north_set(m):
    """北侧：三排断柱 + 尖拱 + 台阶 + 倒卧柱鼓；后方残墙带玫瑰窗；东北 / 西北各一座角墩。"""
    rng = random.Random(501)
    # 第一排（离边界最近、最入镜）：x, 高度, i = 完整柱（带柱头）/ b = 断柱
    front = [(-41, 7.5, "b"), (-34, 3.6, "b"), (-27, 10.5, "i"), (-16.5, 10.5, "i"), (-9, 6.2, "b"), (-1, 14.5, "b"),
             (7, 10.5, "i"), (17.5, 10.5, "i"), (25, 5.0, "b"), (33, 11.5, "b"), (41, 4.5, "b")]
    zf = -44.3
    for i, (x, h, k) in enumerate(front):
        place_column(m, x, zf + rng.uniform(-0.4, 0.4), 1.0, h, k, 100 + i)
    arch_between(m, (-27, zf), (-16.5, zf), 10.5, True, 1.5, 1.0, 11, keep_a=1.0, keep_b=0.55)
    arch_between(m, (7, zf), (17.5, zf), 10.5, True, 1.5, 1.0, 12, keep_a=1.0, keep_b=0.9)
    second = [(-37, 17.0, "b"), (-25, 9.0, "b"), (-13, 19.0, "b"), (-1, 8.0, "b"), (11, 16.0, "b"), (23, 12.5, "i"), (35, 18.0, "b")]
    zs = -48.6
    for i, (x, h, k) in enumerate(second):
        place_column(m, x, zs + rng.uniform(-0.5, 0.5), 1.15, h, k, 200 + i)
    third = [(-31, 19.0), (-19, 15.0), (-7, 19.6), (6, 17.0), (19, 14.0), (31, 19.0)]
    zt = -53.0
    for i, (x, h) in enumerate(third):
        place_column(m, x, zt + rng.uniform(-0.5, 0.5), 1.3, h, "b", 300 + i)
    # 台阶（正中、两侧各一段）
    steps(m, -8.0, 8.0, -41.9, 1.7, 2, 31)
    steps(m, -36.0, -26.0, -41.9, 1.5, 1, 32)
    steps(m, 26.0, 37.0, -41.9, 1.5, 1, 33)
    # 倒卧柱鼓
    for i, (x, z, yaw, r, ln) in enumerate([(-38, -42.8, 0.4, 0.95, 3.2), (-20, -42.6, 2.8, 1.0, 2.6), (-4.5, -42.7, 0.1, 0.9, 3.5),
                                           (12.5, -42.5, 1.2, 1.0, 2.2), (29, -42.8, 3.0, 0.9, 3.0), (39.5, -43.2, 0.5, 0.8, 2.4),
                                           (-14, -46.0, 1.9, 0.9, 2.4), (3.5, -46.2, 0.6, 1.0, 3.2), (21, -46.5, 2.4, 0.9, 2.2)]):
        fallen_drum(m, (x, z), yaw, r, ln, 400 + i, tilt=rng.uniform(-0.08, 0.08), roll=rng.uniform(-0.1, 0.1))
    # 后方残墙（带玫瑰窗）
    zw, thick = -57.0, 1.8
    cx, cy, Rr = -4.0, 12.8, 5.2
    rose = round_hole(cx, cy, Rr + 0.2)
    lan1 = pointed_hole(-14.2, 4.5, 1.15, 4.0, 3.0)
    lan2 = pointed_hole(6.2, 4.5, 1.15, 4.0, 3.0)
    hole = lambda x: rose(x) or lan1(x) or lan2(x)
    top = lambda x: max(8.0, 19.8 - 0.04 * (x - cx) ** 2) - rag(x, 5, 4.5)
    wall_strips(m, -18.0, 10.0, zw, thick, top, hole, 77, strip=0.75)
    rose_window(m, cx, cy, zw + 0.0, Rr, 91, broken_arc=(1.05, 1.9), missing=0.30)
    lancet_window_glass(m, -14.2, 4.5, 1.15, 4.0, 3.0, zw + 0.5, 92)
    lancet_window_glass(m, 6.2, 4.5, 1.15, 4.0, 3.0, zw + 0.5, 93)
    # 两侧残墙
    for (xa, xb, hh, sd, win) in [(-47.0, -21.0, 16.0, 61, [(-40.0, 3.8), (-29.0, 3.4)]), (14.0, 47.0, 17.5, 62, [(24.0, 4.2), (36.0, 3.6)])]:
        holes = [pointed_hole(wx, 4.0, 1.05, 3.6, wh * 0.8) for wx, wh in win]
        h2 = lambda x, holes=holes: next((r for r in (f(x) for f in holes) if r), None)
        t2 = lambda x, hh=hh, sd=sd: hh - rag(x, sd, 6.5) - 0.012 * abs(x) * 3
        wall_strips(m, xa, xb, zw + 1.0, 1.6, t2, h2, sd, strip=0.8)
        for wx, wh in win:
            lancet_window_glass(m, wx, 4.0, 1.05, 3.6, wh * 0.8, zw + 1.5, sd + int(wx))
    # 角墩：东北 / 西北
    for sgn, sd in ((+1, 71), (-1, 72)):
        bx = sgn * 52.0
        for (dx, dz, r, h) in [(0, 0, 1.45, 19.2), (-sgn * 3.6, 1.5, 1.3, 15.0), (sgn * 3.2, 2.8, 1.2, 11.5)]:
            place_column(m, bx + dx, -47.0 + dz, r, h, "b", sd * 10 + int(h))
        wall_strips(m, bx - 5.5, bx + 5.5, -49.5, 2.4, lambda x, s=sd: 14.0 - rag(x, s, 6.0) - 0.4 * abs(x - bx) if False else 13.5 - rag(x, s, 6.5), None, sd, strip=0.9)
    # 北侧碎石堆 / 长椅堆
    for i, (x, z, rad, n, hm) in enumerate([(-36, -42.2, 3.0, 26, 1.6), (-21, -42.0, 2.4, 20, 1.2), (-5, -41.9, 2.0, 16, 0.9), (13, -42.1, 2.6, 22, 1.4),
                                           (30, -41.9, 3.0, 24, 1.5), (-44, -41.8, 2.4, 18, 1.2), (44, -42.4, 2.6, 18, 1.2)]):
        rubble_heap(m, x, z, rad, n, hm, 500 + i)
    pew_pile(m, -23, -44.0, 7, 601, spread=3.2, layers=2)
    pew_pile(m, 22, -44.5, 8, 602, spread=3.4, layers=2)


def side_set(m, sgn, seed):
    """东（sgn=+1）/ 西（sgn=−1）：两排断柱（局部有尖拱）、倾倒长椅堆、碎石堆、倒卧柱鼓。"""
    rng = random.Random(seed)
    xf = sgn * 48.2
    rows = [(-35, 5.5, "b"), (-27, 10.0, "i"), (-17, 10.0, "i"), (-8, 7.0, "b"), (1, 13.0, "b"), (10, 10.0, "i"), (20, 10.0, "i"),
            (29, 4.5, "b"), (37, 8.0, "b")]
    if sgn < 0:       # 西侧换一种断法
        rows = [(-36, 8.0, "b"), (-28, 4.0, "b"), (-19, 10.0, "i"), (-9, 10.0, "i"), (-1, 6.5, "b"), (7, 11.5, "b"), (16, 5.0, "b"),
                (25, 10.0, "i"), (35, 10.0, "i")]
    for i, (z, h, k) in enumerate(rows):
        place_column(m, xf + rng.uniform(-0.3, 0.3), z, 1.0, h, k, seed * 10 + i)
    ints = [(z, h) for (z, h, k) in rows if k == "i"]
    for j in range(0, len(ints) - 1, 2):
        (z1, _), (z2, _) = ints[j], ints[j + 1]
        arch_between(m, (xf, z1), (xf, z2), 10.0, False, 1.5, 1.0, seed * 3 + j, keep_a=1.0, keep_b=1.0 if (j == 0) == (sgn > 0) else 0.6)
    xs = sgn * 54.5
    outer = [(-30, 14.0), (-14, 9.0), (0, 17.0), (16, 11.0), (31, 15.0)]
    for i, (z, h) in enumerate(outer):
        place_column(m, xs + rng.uniform(-0.5, 0.5), z, 1.15, h, "b", seed * 20 + i)
    for i, (z, ln, r) in enumerate([(-31.5, 3.0, 0.9), (-12.5, 2.4, 1.0), (4.5, 3.4, 0.9), (22.5, 2.6, 0.95), (33.5, 2.2, 0.8)]):
        fallen_drum(m, (sgn * (46.9 + rng.uniform(0, 1.2)), z), rng.uniform(0, math.pi), r, ln, seed * 40 + i, tilt=rng.uniform(-0.08, 0.08))
    for i, (z, rad, n, hm) in enumerate([(-39, 2.6, 20, 1.3), (-21.5, 2.4, 18, 1.1), (-3.5, 2.8, 22, 1.4), (14.5, 2.4, 18, 1.1), (30.5, 2.8, 22, 1.4)]):
        rubble_heap(m, sgn * (46.8 + 1.2 * rng.random()), z, rad, n, hm, seed * 50 + i)
    for i, z in enumerate((-23.0, 6.5, 26.5)):
        pew_pile(m, sgn * (51.5 + rng.uniform(-0.5, 1.0)), z, 8, seed * 60 + i, spread=2.8, layers=2)
    # 外排之间的碎石 / 长椅
    for i, z in enumerate((-36, -8, 12, 36)):
        rubble_heap(m, sgn * (59.0 + rng.uniform(-1, 1)), z + rng.uniform(-2, 2), 3.0, 22, 1.6, seed * 70 + i)


def south_set(m, seed=801):
    """南侧（靠近镜头）：只放低矮的东西（≤ 2 m）：碎石堆、倒卧柱鼓、短柱墩（≤ 1.7 m）、倾倒的长椅（≤ 1.6 m）。"""
    rng = random.Random(seed)
    for i, (x, z, rad, n, hm) in enumerate([(-38, 43.5, 3.0, 24, 1.3), (-24, 43.0, 2.2, 16, 0.9), (-8, 43.8, 2.8, 22, 1.2), (8, 43.2, 2.4, 18, 1.0),
                                           (24, 43.8, 3.0, 24, 1.3), (39, 43.2, 2.6, 20, 1.2), (-49, 45.0, 3.4, 26, 1.5), (49, 45.5, 3.4, 26, 1.5)]):
        rubble_heap(m, x, z, rad, n, hm, seed + i, ymax=1.8)
    for i, (x, z, yaw, r, ln) in enumerate([(-30, 44.8, 0.3, 0.8, 2.6), (-14, 45.0, 2.7, 0.9, 2.2), (3, 45.2, 0.9, 0.85, 3.0), (17, 44.9, 2.1, 0.8, 2.4),
                                           (31, 45.1, 0.2, 0.9, 2.8), (-44, 47.5, 1.5, 0.8, 2.4), (44, 47.8, 0.7, 0.85, 2.2)]):
        fallen_drum(m, (x, z), yaw, r, ln, seed + 40 + i, tilt=rng.uniform(-0.05, 0.05))
    # 短柱墩：柱础 + 一两节鼓石（高 ≤ 1.7）
    for i, (x, z) in enumerate([(-34, 47.0), (-20, 48.0), (-4, 47.5), (12, 48.2), (27, 47.2), (40, 47.8), (-47, 50.0), (47, 50.5)]):
        r = rng.uniform(0.85, 1.0)
        with m.at((x, 0, z), rng.uniform(0, TAU)):
            column(m, r, rng.uniform(0.95, 1.5), seed + 80 + i, capital=False, broken=True)
    for i, (x, z) in enumerate([(-27, 49.8), (-10, 50.6), (7, 50.2), (22, 50.4), (36, 50.8)]):
        pew_pile(m, x, z, 5, seed + 120 + i, spread=2.4, layers=1, ymax=1.7)
    # 远一圈的碎石
    for i in range(18):
        x, z = rng.uniform(-60, 60), rng.uniform(51.5, 56)
        rubble_heap(m, x, z, rng.uniform(1.4, 2.4), 12, 0.9, seed + 200 + i, ymax=1.6)


def scatter_outer(meshes):
    """边界外一圈的小碎石（地面起伏、不显得空）：按位置丢进对应的网格。"""
    rng = random.Random(901)
    def accept(x, z):
        return abs(x) >= PLAY_X + 2.0 or abs(z) >= PLAY_Z + 2.0
    pts = poisson(rng, 170, accept, 3.4, (-66, 66, -62, 58))
    for i, (x, z) in enumerate(pts):
        if z > PLAY_Z + 1.5 and abs(x) < PLAY_X + 1.5:
            m = meshes["S"]
        elif z < -PLAY_Z - 1.5 and abs(x) < PLAY_X + 1.5:
            m = meshes["N"]
        elif x > 0:
            m = meshes["E"]
        else:
            m = meshes["W"]
        s = rng.uniform(0.12, 0.42)
        m.rock(STONE, (s, s * 0.8, s * rng.uniform(0.8, 1.3)), (x, 0, z), seed=rng.randint(0, 99999), detail=0, yaw=rng.uniform(0, TAU),
               tint=(rng.uniform(0.75, 1.0),) * 3)


def build_bounds():
    meshes = {"N": Mesh(21), "E": Mesh(22), "W": Mesh(23), "S": Mesh(24)}
    # 边界基座 / 栏杆：四条边，内侧面贴着边界线（|x| = 44.1 / |z| = 40.1）
    L_ns, L_ew = 2 * (PLAY_X + 0.1 + RIM_W), 2 * (PLAY_Z + 0.1)
    with meshes["N"].at((0, 0, -PLAY_Z), math.pi):
        rim_wall(meshes["N"], L_ns, 11)
    with meshes["S"].at((0, 0, PLAY_Z), 0.0):
        rim_wall(meshes["S"], L_ns, 12)
    with meshes["E"].at((PLAY_X, 0, 0), math.pi / 2):
        rim_wall(meshes["E"], L_ew, 13)
    with meshes["W"].at((-PLAY_X, 0, 0), -math.pi / 2):
        rim_wall(meshes["W"], L_ew, 14)
    north_set(meshes["N"])
    side_set(meshes["E"], +1, 3)
    side_set(meshes["W"], -1, 4)
    south_set(meshes["S"])
    scatter_outer(meshes)
    parts = []
    for key, name in (("N", "BOUNDS_NORTH"), ("E", "BOUNDS_EAST"), ("W", "BOUNDS_WEST"), ("S", "BOUNDS_SOUTH")):
        meshes[key].paint(stone_paint({"N": 1, "E": 2, "W": 3, "S": 4}[key]))
        parts.append(Part(name, "ARENA_BOUNDS", meshes[key]))
    if os.environ.get("ARENA_AO", "1") != "0":
        C.bake_ao(list(meshes.values()), skip_mats=(WIN_C, WIN_R, FLAME), strength=0.62)
    return parts


# =====================================================================
# 场内道具（ARENA_PROPS）：低矮（≤ 0.6 m）、稀疏、中心 18 m 半径内保持干净
# =====================================================================
def candelabra_fallen(m, x, z, yaw, seed):
    """倒在地上的黄铜烛台：横躺的灯柱 + 底座 + 三根侧枝，枝头小杯。最高约 0.3 m。"""
    rng = random.Random(seed)
    with m.at((x, 0.06, z), yaw, math.pi / 2):
        m.lathe(BRASS, [(0.028, -0.72), (0.045, -0.42), (0.030, -0.12), (0.052, 0.22), (0.034, 0.52), (0.026, 0.72)], 6,
                smooth=True, share=True, cap_bottom=True, cap_top=True)
        m.lathe(BRASS, [(0.0, -0.74), (0.17, -0.74), (0.20, -0.70), (0.06, -0.62)], 8, smooth=False, cap_bottom=True, cap_top=False)
        for k in range(3):
            a = rng.uniform(0, TAU)
            for sgn in (-1, 1):
                if k == 2 and sgn == 1:
                    continue
                ln = rng.uniform(0.22, 0.34)
                tip = (math.cos(a) * ln * sgn, 0.12 * k + 0.05 * (k - 1), math.sin(a) * ln * sgn)
                # 侧枝：从灯柱上的 (0, y0, 0) 到 tip 的细长盒子（沿方向拉伸）
                y0 = -0.1 + 0.18 * k
                d = np.array(tip) - np.array((0, y0, 0))
                L = float(np.linalg.norm(d))
                yaw_ = math.atan2(d[0], d[2])
                pitch_ = -math.asin(d[1] / max(L, 1e-6))
                with m.at((0, y0, 0), yaw_, pitch_):
                    m.box(BRASS, (0.022, 0.022, L), pos=(0, 0, L / 2), anchor="center")
                with m.at(tip):
                    m.lathe(BRASS, [(0.020, 0.0), (0.045, 0.030), (0.040, 0.055)], 6, smooth=False, cap_bottom=True, cap_top=False)


def candle_stand(m, x, z, seed):
    """立着的小烛台（有火苗）：总高 ≤ 0.56 m。"""
    rng = random.Random(seed)
    with m.at((x, 0, z), rng.uniform(0, TAU)):
        m.lathe(BRASS, [(0.0, 0.0), (0.13, 0.0), (0.14, 0.02), (0.045, 0.045), (0.028, 0.20), (0.05, 0.27), (0.05, 0.29)], 8,
                smooth=True, share=False, cap_bottom=False, cap_top=True)
        m.lathe(BRASS, [(0.026, 0.29), (0.026, 0.47)], 6, smooth=True, cap_bottom=False, cap_top=True, tint=(1.15, 1.1, 0.95))
        m.lathe(FLAME, [(0.0, 0.47), (0.028, 0.50), (0.020, 0.54), (0.0, 0.575)], 6, smooth=True, share=True, cap_bottom=False, cap_top=False)


def glass_cluster(m, x, z, rng, n):
    cols = [(0.62, 0.92, 1.0), (0.95, 0.55, 0.78), (1.0, 0.86, 0.52), (0.55, 0.78, 1.0)]
    base = rng.choice(cols)
    for _ in range(n):
        ang = rng.uniform(0, TAU)
        r = rng.uniform(0.05, 0.55)
        cx, cz = x + r * math.cos(ang), z + r * math.sin(ang)
        s = rng.uniform(0.07, 0.24)
        pts = []
        k = rng.choice((3, 3, 4))
        a0 = rng.uniform(0, TAU)
        for j in range(k):
            a = a0 + j * TAU / k + rng.uniform(-0.4, 0.4)
            rr = s * rng.uniform(0.55, 1.0)
            pts.append((cx + rr * math.cos(a), 0.012 + rng.uniform(0, 0.05) + (0.06 if rng.random() < 0.25 and j == 0 else 0.0), cz - rr * math.sin(a)))
        t = rng.uniform(0.75, 1.05)
        tint = (base[0] * t, base[1] * t, base[2] * t)
        m.poly(SHARD, pts, tint=tint)


def crack_decal(m, x, z, rng, length):
    """地面裂缝贴片：随机折线 + 分叉，深色窄带贴地（y = 0.014）；走到场外 / 中心空地就截断。"""
    def inside(px, pz):
        return abs(px) < PLAY_X - 0.9 and abs(pz) < PLAY_Z - 0.9 and math.hypot(px, pz) > CLEAN_R + 0.4

    ang = rng.uniform(0, TAU)
    pts, widths = [(x, z)], [0.05]
    px, pz = x, z
    n = max(4, int(length / 0.9))
    for k in range(n):
        ang += rng.uniform(-0.55, 0.55)
        qx, qz = px + math.cos(ang) * length / n, pz + math.sin(ang) * length / n
        if not inside(qx, qz):
            break
        px, pz = qx, qz
        pts.append((px, pz))
        widths.append(rng.uniform(0.04, 0.13) * (1.0 - 0.6 * k / n))
    if len(pts) < 3:
        return
    m.strip_xz(STONE, pts, widths, y=0.014, tint=(0.16, 0.18, 0.20))
    if len(pts) >= 5 and rng.random() < 0.8:       # 一条分叉
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
            bw.append(max(0.03, bw[-1] * 0.7))
        if len(bp) >= 2:
            m.strip_xz(STONE, bp, bw, y=0.014, tint=(0.16, 0.18, 0.20))


def build_props():
    """ARENA_PROPS：碎石、碎玻璃片、倒地烛台、烛台、地面裂缝、断石板。全部在可活动区域里、≤ 0.6 m、离中心 ≥ 18 m。"""
    m = Mesh(41)
    rng = random.Random(41)
    R0 = CLEAN_R + 1.0

    def ok(x, z):
        r = math.hypot(x, z)
        if abs(x) > PLAY_X - 1.2 or abs(z) > PLAY_Z - 1.2 or r < R0:
            return False
        return rng.random() < 0.18 + 0.82 * float(T.smoothstep(20.0, 44.0, r))

    box = (-PLAY_X, PLAY_X, -PLAY_Z, PLAY_Z)
    for i, (x, z) in enumerate(poisson(rng, 70, ok, 6.0, box)):              # 碎石簇
        s0 = rng.uniform(0.14, 0.30)
        m.rock(STONE, (s0, s0 * 0.82, s0 * rng.uniform(0.8, 1.25)), (x, 0, z), seed=rng.randint(0, 99999), detail=0, yaw=rng.uniform(0, TAU),
               tint=(rng.uniform(0.7, 1.0),) * 3)
        for _ in range(rng.randint(2, 5)):
            a, d = rng.uniform(0, TAU), rng.uniform(0.25, 0.9)
            s1 = rng.uniform(0.05, 0.16)
            m.rock(STONE, (s1, s1 * 0.8, s1), (x + d * math.cos(a), 0, z + d * math.sin(a)), seed=rng.randint(0, 99999), detail=0, yaw=rng.uniform(0, TAU),
                   tint=(rng.uniform(0.65, 1.0),) * 3)
    for (x, z) in poisson(rng, 46, ok, 5.0, box):                              # 碎玻璃
        glass_cluster(m, x, z, rng, rng.randint(3, 6))
    for (x, z) in poisson(rng, 14, ok, 11.0, box):                             # 裂缝
        crack_decal(m, x, z, rng, rng.uniform(3.0, 8.5))
    for (x, z) in poisson(rng, 24, ok, 6.0, box):                              # 断石板（薄、平、略斜）
        w, d_ = rng.uniform(0.45, 1.0), rng.uniform(0.3, 0.7)
        m.box(STONE, (w, rng.uniform(0.05, 0.10), d_), pos=(x, 0.0, z), yaw=rng.uniform(0, TAU), pitch=rng.uniform(-0.12, 0.12), roll=rng.uniform(-0.12, 0.12),
              chamfer=0.02, tint=(rng.uniform(0.7, 1.0),) * 3)
    for i, (x, z) in enumerate(poisson(rng, 7, lambda x, z: ok(x, z) and math.hypot(x, z) > 24, 12.0, box)):   # 倒地烛台
        candelabra_fallen(m, x, z, rng.uniform(0, TAU), 700 + i)
    for i, (x, z) in enumerate(poisson(rng, 4, lambda x, z: ok(x, z) and math.hypot(x, z) > 26, 20.0, box)):   # 立着的烛台
        candle_stand(m, x, z, 710 + i)
    m.paint(stone_paint(7))
    if os.environ.get("ARENA_AO", "1") != "0":
        C.bake_ao([m], skip_mats=(FLAME, SHARD), samples=10, dist=1.2, strength=0.5)
    return [Part("PROPS_FLOOR_SCATTER", "ARENA_PROPS", m)]


# =====================================================================
# 彩窗光柱（ARENA_LIGHTS）：半透明体积光片，从北侧彩窗斜射向场内；透明度沿长度 / 宽度渐隐（顶点色 A）
# =====================================================================
SHAFTS = [  # (材质, 窗口 x, 窗口 z, 窗口顶高, 落点 x, 落点 z, 顶宽, 底宽)
    (SHAFT_C, -26.0, -52.5, 15.5, -21.0, -31.0, 2.6, 4.2),
    (SHAFT_R, -9.0, -54.0, 16.0, -5.5, -27.0, 2.4, 3.8),
    (SHAFT_C, 8.0, -54.0, 15.0, 12.5, -28.0, 2.6, 4.0),
    (SHAFT_R, 25.0, -52.0, 14.0, 29.0, -32.0, 2.4, 3.8),
    (SHAFT_C, -39.0, -51.0, 13.5, -35.0, -34.0, 2.2, 3.6),
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
    # 地面光斑：落点处沿光线方向拉长的柔边菱形（9 点网格，边缘 A = 0）
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
            aa.append(1.0 if (gi == 1 and gj == 1) else (0.45 if (gi == 1 or gj == 1) else 0.0))
    FF = []
    for gi in range(2):
        for gj in range(2):
            a = gi * 3 + gj
            FF.append([a, a + 1, a + 4, a + 3])
    m.add(np.array(pp), FF, mat, False, tint=(1, 1, 1), alpha=np.array(aa) * 0.55)
    return m


def build_lights():
    parts = []
    for i, sp in enumerate(SHAFTS):
        parts.append(Part(f"LIGHT_SHAFT_{i}", "ARENA_LIGHTS", shaft_mesh(sp, 900 + i)))
    return parts


def build():
    parts = []
    for name, fn in (("floor", build_floor), ("bounds", build_bounds), ("props", build_props), ("lights", build_lights)):
        if name in PARTS:
            parts += fn()
    return parts
