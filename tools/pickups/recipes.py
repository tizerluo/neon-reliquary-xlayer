"""掉落道具 · 游戏版配方：碎片（shard）/ 圣瓶（vial）；圣物匣在 chest.py。

每个配方 build_<id>() 返回 [Part, ...]：Part = (节点名, Mesh, 材质列表, 节点位置)。
坐标：Blender Z 向上（导出后 glTF Y 向上）；道具正面朝 -Y（导出后 glTF +Z，游戏相机一侧）。
材质命名遵守游戏选择性辉光的按名权重：Glow → 0.5（强辉光，已把强度压低）、inlay / rune → 0.25、其余 0.06。
"""

import math
import random
from collections import namedtuple

from mathutils import Vector

from .geo import Mesh, make_material

Part = namedtuple("Part", "name mesh mats loc")

# 语义色（不可改色相）：青 = 成长、绿 = 回复、金 = 超频
COLORS = {"shard": "#86d9e6", "vial": "#87ffb5", "chest": "#ffd291"}

# 三角面 / 材质数预算（硬性规格）
BUDGET = {"shard": 80, "vial": 400, "chest": 1500}
MAT_LIMIT = {"shard": 2, "vial": 3, "chest": 4}


def lerp(a, b, t):
    return a + (b - a) * t


# =====================================================================
# 成长碎片 · 不对称刻面水晶簇：一根主晶体 + 两根斜出的小晶体，棱面交替明暗，内部发光
# =====================================================================
def _crystal(m, origin, axis, a, b, R, prof, sides, rot, seed, mats, glow_edges, jitter=0.16):
    """沿 axis 的双锥晶体：prof = [(相对高度, 相对半径)...] 夹在下尖（-a）和上尖（+b）之间，R 为腰部半径。
    每个顶点半径 / 角度带确定性抖动 → 刻面不对称。mats = (晶体, 发光)；glow_edges：哪些棱面用发光材质（按 (段, 边) 判断）。"""
    rng = random.Random(seed)
    with m.frame(origin, axis):
        rings = []
        for (h, r) in prof:
            z = h * b if h >= 0 else h * a                           # 高度按上 / 下半段缩放
            ring = []
            for k in range(sides):
                ang = rot + math.tau * k / sides + rng.uniform(-0.10, 0.10)
                rr = R * r * (1 + rng.uniform(-jitter, jitter))
                ring.append((rr * math.cos(ang), rr * math.sin(ang), z + rng.uniform(-0.012, 0.012)))
            rings.append(m.vs(ring))
        lo = m.v((rng.uniform(-0.01, 0.01), rng.uniform(-0.01, 0.01), -a))
        hi = m.v((rng.uniform(-0.015, 0.015), rng.uniform(-0.015, 0.015), b))
        ref = m.pt((0, 0, (b - a) / 2))
        m.fan(rings[0], lo, lambda e: mats[1] if (-1, e) in glow_edges else mats[0], ref=ref)
        m.loft(rings, lambda k, e: mats[1] if (k, e) in glow_edges else mats[0], ref=ref)
        m.fan(rings[-1], hi, lambda e: mats[1] if (len(rings) - 1, e) in glow_edges else mats[0], ref=ref)


def build_shard():
    # 晶体本体取同色相的深青（#86d9e6 同为 188° 色相），发光件用语义色原值；亮暗面的反差表现“内部有光”
    crystal = make_material("Shard Crystal", "#2897ab", metal=0.0, rough=0.10, spec=0.7,
                            emit=COLORS["shard"], strength=0.55, cull=True)
    glow = make_material("Shard Glow", COLORS["shard"], metal=0.0, rough=0.25, spec=0.4,
                         emit=COLORS["shard"], strength=1.6, cull=True)
    C, G = 0, 1
    m = Mesh()
    # 主晶体：六棱，腰部最宽，上下收尖；腰带上方一圈（段 1）亮、下尖几个面也亮 → 像内部有光透出来
    _crystal(m, (0.0, 0.0, 0.0), (0.10, 0.04, 1.0), 0.30, 0.30, 0.095, [(-0.45, 0.62), (0.0, 1.0), (0.55, 0.74)],
             6, 0.2, 11, (C, G), glow_edges={(1, 0), (1, 2), (1, 4), (-1, 1), (-1, 4)}, jitter=0.12)
    # 两根斜出的小晶体（五棱），根在主晶体下半段，朝外朝上
    _crystal(m, (-0.062, 0.020, -0.075), (-0.62, 0.22, 0.75), 0.13, 0.205, 0.062, [(-0.4, 0.95), (0.45, 0.80)],
             5, 0.5, 23, (C, G), glow_edges={(0, 1), (0, 3), (-1, 0)})
    _crystal(m, (0.068, -0.026, -0.105), (0.55, -0.30, 0.78), 0.11, 0.16, 0.050, [(-0.4, 0.95), (0.45, 0.80)],
             5, 1.1, 31, (C, G), glow_edges={(0, 0), (0, 2)})
    return [Part("SHARD", m, [crystal, glow], (0, 0, 0))]


# =====================================================================
# 回复圣瓶 · 绿色光液圆肚瓶 + 银色瓶笼（上下环 + 四根竖条）+ 暗色木塞；液体半透明发光
# =====================================================================
LIQUID_ALPHA = 0.70
LIQUID_BASE_STRENGTH = 1.8          # 不透明时的“目标亮度”；写进文件的强度 = 它 × alpha（发光按透明度预乘）

VIAL_PROFILE = [(0.0, -0.340), (0.115, -0.332), (0.200, -0.290), (0.248, -0.200), (0.250, -0.100),
                (0.205, -0.005), (0.120, 0.070), (0.078, 0.140), (0.074, 0.240), (0.092, 0.270)]


def _vial_r(z, off=0.0):
    """瓶身剖面在高度 z 处的半径（折线插值）。"""
    for (r0, z0), (r1, z1) in zip(VIAL_PROFILE, VIAL_PROFILE[1:]):
        if z0 <= z <= z1:
            return lerp(r0, r1, (z - z0) / (z1 - z0)) + off
    return VIAL_PROFILE[-1][0] + off


def build_vial():
    liquid = make_material("Vial Glow", "#2fbf6f", metal=0.0, rough=0.2, spec=0.25,
                           emit=COLORS["vial"], strength=round(LIQUID_BASE_STRENGTH * LIQUID_ALPHA, 4), alpha=LIQUID_ALPHA)
    silver = make_material("Vial Cage Silver", "#e8edf2", metal=0.7, rough=0.40)
    cork = make_material("Vial Stopper", "#4a3424", metal=0.0, rough=0.85, spec=0.2)
    LIQ, CAGE, CORK = 0, 1, 2
    m = Mesh()
    # 液体 / 玻璃：八棱车削、平滑法线（半透明双面）
    m.lathe(VIAL_PROFILE, 8, LIQ, smooth=True, cap_top=False)
    # 瓶笼：下环（贴着下腹）+ 上环（扣住瓶颈），半径 = 瓶身剖面外偏一点
    low = [(-0.312, 0.012), (-0.288, 0.017), (-0.248, 0.017), (-0.226, 0.012)]
    m.lathe([(_vial_r(z, o), z) for z, o in low], 8, CAGE, cap_bottom=False, cap_top=False)
    m.lathe([(0.094, 0.196), (0.108, 0.208), (0.108, 0.250), (0.100, 0.262)], 8, CAGE, cap_bottom=False, cap_top=False)
    # 四根竖条：沿瓶身剖面外偏一点，脊形截面
    zs = [-0.238, -0.15, -0.06, 0.03, 0.10, 0.20]
    for k in range(4):
        ang = math.radians(45 + 90 * k)
        c, s = math.cos(ang), math.sin(ang)
        path, nrm = [], []
        for z in zs:
            r = _vial_r(z, 0.012)
            path.append((r * c, r * s, z))
            slope = (_vial_r(z + 0.01) - _vial_r(z - 0.01)) / 0.02
            n = Vector((c, s, -slope)).normalized()
            nrm.append(n)
        m.rib(CAGE, path, nrm, 0.016, 0.018, inset=None)
    # 瓶塞：木塞（略外张的锥台）+ 顶部小圆顶
    m.lathe([(0.082, 0.236), (0.100, 0.268), (0.106, 0.318), (0.088, 0.344)], 8, CORK, cap_bottom=False)
    return [Part("VIAL", m, [liquid, silver, cork], (0, 0, 0))]


RECIPES = {"shard": build_shard, "vial": build_vial}
