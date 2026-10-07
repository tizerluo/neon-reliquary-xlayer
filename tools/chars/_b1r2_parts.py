"""Boss 1（苍白巨龙）第二轮私有工具：刻面冰晶、冰晶 / 甲板贴图、贴合曲面的甲片。

不改 kit 与 _bossA_common（后者被 Boss 0 / Boss 2 共用）：
- kit.spike / _bossA_common.shards 只有 4–5 面、无 UV，平涂材质下是一团白；
  这里的 crystals() 是 6 面刻面晶柱（肩部收棱、偏心尖顶、逐顶点半径抖动），UV 的 u 在每个刻面内走 0→1、
  v 从根部 0 走到尖端 1，配合 crystal_maps() 做出“根部青光渐变 + 刻面中心内部青光 + 棱线霜白”。
- hull_patch() 在任意参数曲面上取一块 (a, v) 区域外推成有厚度的贴合甲片，并返回边界点列用于滚边。
"""

import math
import random

import bmesh
import numpy as np
from mathutils import Vector

from kit.core import TAU, bm_object, box_blur, finish, lerp, orient, surface


# ===== 刻面冰晶 =====
def crystals(name, items, mats, seed=0, double=False):
    """一批刻面冰晶：items 为 [(根, 尖, 半径[, 面数]), ...]；double=True 时两端都收尖（悬浮冰棱）。
    平直着色（刻面），UV：u 每个刻面 0→1，v 根部 0 → 尖端 1。"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rng = random.Random(seed)

    def face(pairs, outward):
        """按外法向排好顶点顺序后建面，并逐角写 UV。"""
        vs = [p[0] for p in pairs]
        n = (vs[1].co - vs[0].co).cross(vs[2].co - vs[0].co)
        if n.dot(outward) < 0:
            pairs = list(reversed(pairs))
        try:
            f = bm.faces.new([p[0] for p in pairs])
        except ValueError:
            return
        for loop, (_, uv) in zip(f.loops, pairs):
            loop[uvl].uv = uv

    for it in items:
        base, tip, r = Vector(it[0]), Vector(it[1]), it[2]
        sides = it[3] if len(it) > 3 else 6
        d = tip - base
        L = d.length
        if L < 1e-5:
            continue
        n = d / L
        a = n.orthogonal().normalized()
        b = n.cross(a)
        ph = rng.random() * TAU
        jit = [1 + (rng.random() - 0.5) * 0.30 for _ in range(sides)]
        # 截面环：(沿轴比例 t, 半径倍率)；根部略收（埋进躯干），中段最宽，肩部收棱后接尖顶
        prof = [(0.34, 1.0), (0.62, 0.96)] if double else [(0.0, 0.70), (0.12, 1.0), (0.64, 0.90)]
        rings = []
        for t, k in prof:
            row = []
            for q in range(sides):
                ang = ph + q / sides * TAU
                rr = r * k * jit[q]
                row.append((bm.verts.new(base + d * t + (a * math.cos(ang) + b * math.sin(ang)) * rr), t))
            rings.append(row)
        off = (a * math.cos(ph * 1.7) + b * math.sin(ph * 1.7)) * r * 0.22 * rng.random()
        apex = bm.verts.new(tip + off)
        center = base + d * 0.5
        for i in range(len(rings) - 1):
            for q in range(sides):
                q2 = (q + 1) % sides
                (v0, t0), (v1, _), (v2, t1), (v3, _) = rings[i][q], rings[i][q2], rings[i + 1][q2], rings[i + 1][q]
                mid = (v0.co + v1.co + v2.co + v3.co) / 4
                face([(v0, (0, t0)), (v1, (1, t0)), (v2, (1, t1)), (v3, (0, t1))], mid - center)
        top = rings[-1]
        for q in range(sides):
            q2 = (q + 1) % sides
            mid = (top[q][0].co + top[q2][0].co + apex.co) / 3
            face([(top[q][0], (0, top[q][1])), (top[q2][0], (1, top[q][1])), (apex, (0.5, 1.0))], mid - center)
        bot = rings[0]
        if double:
            apex2 = bm.verts.new(base - off * 0.5)
            for q in range(sides):
                q2 = (q + 1) % sides
                mid = (bot[q][0].co + bot[q2][0].co + apex2.co) / 3
                face([(bot[q][0], (0, bot[q][1])), (bot[q2][0], (1, bot[q][1])), (apex2, (0.5, 0.0))], mid - center)
        else:
            face([(v, (0.5 + 0.5 * math.cos(q / sides * TAU), 0.0)) for q, (v, _) in enumerate(bot)], -n)
    return bm_object(name, bm, mats, smooth=False)


def crystal_maps(glow=(0.30, 0.86, 1.0), deep=(0.015, 0.06, 0.15), pale=(0.36, 0.62, 0.80), size=512, seed=4):
    """冰晶贴图（配合 crystals 的 UV）：
    底色：根部深冰蓝 → 尖端浅冰青，棱线一圈霜白；
    自发光：根部强青光指数衰减 + 刻面中心一道“内部光柱” + 斜向内部裂纹微光，尖端几乎不发光（保住玻璃反射）。"""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size      # 第 0 行为 v=0（根部）
    v, u = y, x
    edge = np.exp(-(np.minimum(u, 1 - u) / 0.045) ** 2)
    core = np.exp(-((u - 0.5) / 0.17) ** 2)
    root = np.exp(-v / 0.17)
    noise = box_blur(rng.random((size, size)).astype(np.float32), 10)
    noise = (noise - noise.min()) / max(1e-6, noise.max() - noise.min())
    crack = (0.5 + 0.5 * np.sin(TAU * (u * 1.3 + v * 2.6) + noise * 4.0)) ** 16
    t = np.clip((v - 0.10) / 0.9, 0, 1) ** 0.8
    base = np.array(deep)[None, None, :] * (1 - t[..., None]) + np.array(pale)[None, None, :] * t[..., None]
    base = base + edge[..., None] * (0.20 + 0.25 * v[..., None]) * np.array((0.85, 0.95, 1.0))[None, None, :]
    fade = (1 - v) ** 1.6
    glow_v = 1.0 * root + 0.42 * core * fade + 0.35 * crack * fade + 0.10 * edge * (1 - v)
    em = np.stack([glow_v * c for c in glow], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), None


def ring_maps(glow=(0.30, 0.86, 1.0), size=256, dashes=24):
    """节间发光环：沿环（u）分段的亮 / 暗光条，两侧（v 边缘）收暗，像一圈机械灯带。"""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size
    dash = np.clip(np.abs(((x * dashes) % 1.0) - 0.5) * 2, 0, 1)
    band = 0.55 + 0.45 * (dash < 0.8)
    edge = np.clip(np.sin(math.pi * y), 0, 1) ** 0.5
    em = np.stack([band * edge * c for c in glow], axis=2)
    return np.clip(em * 0.4, 0, 1), np.clip(em, 0, 1), None


# ===== 贴合曲面的甲片 =====
def hull_patch(name, surf, a_rng, v_rng, lift, depth, mats, ref, nu=10, nv=8, flare=0.0, flare_side=0.0,
               uv_scale=(1.0, 1.0)):
    """在参数曲面 surf(a, v, lift) 上取一块区域做有厚度的甲片。
    a_rng(vv) -> (a0, a1)：随 vv（0 后缘 → 1 前缘）变化的横向范围，可做出前窄后宽的楔形；
    v_rng = (v0, v1)；flare：后缘（vv=0）额外外翘量；flare_side：两侧边缘额外外翘量。
    返回 (对象, 外表面边界点列)。"""
    v0, v1 = v_rng

    def pt(uu, vv, extra=0.0):
        a0, a1 = a_rng(vv)
        lf = lift + flare * (1 - vv) ** 2 + flare_side * (2 * uu - 1) ** 4 + extra
        return surf(lerp(a0, a1, uu), lerp(v0, v1, vv), lf)
    obj = surface(name, pt, nu, nv, mats, uvfn=lambda uu, vv: (uu * uv_scale[0], vv * uv_scale[1]))
    orient(obj, ref)
    obj = finish(obj, depth, -1.0, 0)
    loop = [pt(i / nu, 0.0, 0.004) for i in range(nu + 1)] + [pt(1.0, j / nv, 0.004) for j in range(1, nv + 1)] + \
           [pt(1 - i / nu, 1.0, 0.004) for i in range(1, nu + 1)] + [pt(0.0, 1 - j / nv, 0.004) for j in range(1, nv)]
    return obj, loop
