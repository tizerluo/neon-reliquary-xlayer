"""Boss 1（苍白巨龙）第三轮私有模块：盘身的叠瓦鳞片 / 腹板贴图。

躯干背甲与腹板现在是真实的起伏几何（叠瓦：每片鳞自由边翘起、向头端缓缓压低、被下一片的自由边压住），
这里的贴图是一张“单片鳞 / 单块腹板”的平铺单元，UV 与几何一一对应：u 横跨一片鳞（0..1），v 从自由边 0 → 被压住的一端 1。
三层材质拉开：亮银鳞面（自由边一道高光）/ 深冰蓝底与凹缝 / 青色发光缝。
"""

import math

import numpy as np

from kit.core import box_blur


def _ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def scale_tile(size=256, seed=3, glow=(0.20, 0.82, 1.0)):
    """亮银鳞片单元（u 横跨一片鳞，v 自自由边 0 到被压住端 1）：
    自由边按“U 形”弧线向两侧退让，鳞片两侧上方（vv<0）是被邻排鳞压住的深冰蓝暗缝，缝边一线青光；
    自由边一道高光，向压住端渐暗，鳞面有横向拉丝。返回 (base, emission)。"""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    cen = np.cos(math.pi * (u - 0.5)) ** 2                      # 鳞片中线更鼓
    x = (u - 0.5) * 2
    edge = 0.46 * (1 - np.sqrt(np.clip(1 - x * x, 0, 1)))          # 半圆形自由边：中线最靠前，两侧退到 v=0.46
    vv = v - edge
    gap = 1 - _ss(-0.025, 0.012, vv)                             # vv<0：被邻排鳞压住的暗缝
    lip = np.exp(-(np.maximum(vv, 0) / 0.050) ** 2)
    body = (1 - _ss(0.0, 0.80, np.maximum(vv, 0))) ** 1.0
    tone = 0.14 + 0.50 * body * (0.82 + 0.18 * cen) + 0.62 * lip
    tone = tone * (1 - 0.88 * _ss(0.80, 0.97, v))                # 被压住端凹缝压得很暗
    tone = tone * (1 - 0.90 * gap) + 0.05 * gap
    brush = box_blur(rng.random((size, size)).astype(np.float32), 1)
    streak = box_blur(rng.random((size, 1)).astype(np.float32) * np.ones((1, size), np.float32), 1)
    tone = tone * (0.93 + 0.10 * (brush - 0.5) + 0.05 * (streak - 0.5))
    silver = np.array((0.80, 0.87, 0.95), np.float32)
    deep = np.array((0.030, 0.090, 0.22), np.float32)
    mix = np.clip(tone, 0, 1)[..., None]
    base = deep[None, None, :] * (1 - mix) + silver[None, None, :] * mix
    seam = np.exp(-(vv / 0.022) ** 2) * (1 - _ss(0.0, 0.05, vv))                 # 邻排鳞自由边下的暗缝边
    em_v = 0.50 * seam * (0.4 + 0.6 * (1 - cen)) + 0.45 * np.exp(-((v - 0.955) / 0.030) ** 2) + 0.06 * lip
    em = np.stack([em_v * c for c in glow], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1)


def belly_tile(size=256, seed=5, glow=(0.20, 0.82, 1.0)):
    """深冰蓝分节腹板单元（u 横跨整条腹面，v 一块板）：板缘一圈银蓝滚边、中线微亮、两侧小铆钉、板缝一线青光。"""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    dome = np.sin(math.pi * u) ** 0.8
    rim = np.exp(-(v / 0.040) ** 2) * (0.5 + 0.5 * dome)
    body = (1 - _ss(0.0, 0.9, v)) ** 1.1
    tone = 0.12 + 0.34 * body * (0.55 + 0.45 * dome) + 0.45 * rim
    nz = box_blur(rng.random((size, size)).astype(np.float32), 2)
    tone = tone * (0.94 + 0.12 * (nz - 0.5))
    navy = np.array((0.025, 0.075, 0.190), np.float32)
    steel = np.array((0.34, 0.58, 0.86), np.float32)
    mix = np.clip(tone, 0, 1)[..., None]
    base = navy[None, None, :] * (1 - mix) + steel[None, None, :] * mix
    # 板侧一对小铆钉
    for cx in (0.07, 0.93):
        d = np.sqrt(((u - cx) * 1.0) ** 2 + ((v - 0.48) * 1.0) ** 2)
        base = base + np.exp(-(d / 0.022) ** 2)[..., None] * 0.55
    ridge = np.exp(-((u - 0.5) / 0.012) ** 2) * (1 - rim)
    base = base + ridge[..., None] * 0.08
    groove = np.exp(-((v - 0.950) / 0.034) ** 2) * (0.30 + 0.70 * dome)
    em_v = 0.85 * groove + 0.20 * rim * dome + 0.10 * ridge + 0.11 * (0.35 + 0.65 * dome) * (1 - groove)   # 板面一层深冰蓝自发光（背光时不发黑）
    em = np.stack([em_v * c for c in glow], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1)
