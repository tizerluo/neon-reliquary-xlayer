"""Boss 7（灰烬炽天使）第五轮私有贴图：把大面积自发光改成“细线 / 刃口 / 少量熔缝”。

背景：游戏里材质经 glow.js 再乘 1.1–1.2、ACES 曝光 1.2 并叠辉光；整片羽毛 / 钢甲 / 长袍带满幅发光贴图（强度 1.5–3.6）
会糊成一团橙光。这里的贴图只在下列位置留发光：
- 翼羽（plume_maps_r5）：最外侧一条细的炽热刃口线（贴着羽片外轮廓，含羽尖收拢处）；“羽根黑 → 刃口橙红”
  改由基础色（albedo 渐变）承担，不再整片发光；
- 剑刃（blade_maps_r5）：刃口一条细发光带 + 少量熔缝；
- 长袍 / 内裙 / 垂饰（burn_cloth_maps_r5）：电路细线 + 下摆一道燃烧线，去掉“燃烧线以下整片焦黑区”的底光。
不改 kit，缺的东西在这里复制 / 改写。
"""

import numpy as np

from kit.core import TAU, box_blur, height_normal, circuit_maps

from chars._b7_lib import ember_crack_maps
from chars._b7r3_parts import sstep, plume_width   # noqa: F401


def _ramp3(k1, k2, c0, c1, c2):
    """三色渐变：k1 控制 c0→c1，k2 控制 c1→c2（k 为 (H, W, 1)）。"""
    a, b, c = (np.array(x, np.float32)[None, None, :] for x in (c0, c1, c2))
    r = a * (1 - k1) + b * k1
    return r * (1 - k2) + c * k2


def plume_maps_r5(emit_rgb, root_rgb, mid_rgb, tip_rgb, gold_rgb, size=1024, seed=5, barbs=44, edge=0.20, tip=0.46,
                  rib=0.9, rib_w=0.05, line=0.06, line_gain=1.0, heat_alb=1.0, shoulder=0.0, shoulder_w=0.20,
                  deep_rgb=(0.52, 0.07, 0.02), hot_rgb=(1.0, 0.82, 0.50),
                  alb0=(0.34, 0.050, 0.016), alb1=(0.78, 0.22, 0.060), alb2=(0.90, 0.46, 0.16)):
    """第五轮刃羽（UV 同 ridge_blade：u 沿羽长、v 沿宽度，中脊 v=0.5）。
    - 基础色：羽根灰烬黑 → 羽身炭灰，外缘与羽尖（与第四轮相同的 hf 分布）渐变成橙红 albedo（alb0→alb1→alb2），
      承担“羽根黑 → 刃口橙红”的读感；
    - 发光：只在最外侧一条细刃口线（半宽的 line 倍、自羽根向尖微微变宽、边缘轻微起伏；可选 shoulder：线内侧一圈快速衰减的暗红肩），
      颜色沿羽长深红 → 橙 → 近金白；
      羽面、羽尖填充、火星、环境底光全部去掉。返回 (base, emission, normal)。"""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    c = np.abs(v - 0.5) * 2
    t1 = sstep(0.0, 0.40, u)
    t2 = sstep(0.35, 1.0, u)
    phase = (u - 0.30 * c) * barbs + 0.6 * np.sin(u * 9.0 + seed)
    barb = (0.5 + 0.5 * np.sin(TAU * phase)) ** 3
    noise = box_blur(rng.random((size, size)).astype(np.float32), 3) - 0.5
    cloud = box_blur(rng.random((size, size)).astype(np.float32), 30) - 0.5
    spine = np.exp(-(c / rib_w) ** 2) * sstep(0.02, 0.10, u) * (1 - sstep(0.78, 0.94, u))
    jag = np.clip(1 + (box_blur(rng.random((size, size)).astype(np.float32), 5) - 0.5) * 20, 0.35, 2.0)
    w = edge * (0.30 + 1.45 * u) * jag
    band = np.clip((c - (1 - w)) / np.maximum(w, 1e-3), 0, 1) ** 1.2 * sstep(0.06, 0.40, u)
    tipheat = sstep(1 - tip, 1.0, u) ** 1.4 * (0.30 + 0.70 * c ** 1.4)
    hf = np.clip(np.maximum(band, tipheat), 0, 1)
    # --- 基础色：暗羽 + 橙红 albedo 渐变 ---
    col = np.array(root_rgb)[None, None, :] * (1 - t1[..., None]) + np.array(mid_rgb)[None, None, :] * t1[..., None]
    col = col * (1 - t2[..., None] * 0.6) + np.array(tip_rgb)[None, None, :] * t2[..., None] * 0.6
    base = col * (0.78 + 0.22 * barb[..., None] + noise[..., None] * 0.25 + cloud[..., None] * 1.0)
    k1 = sstep(0.0, 0.55, hf)[..., None]
    k2 = sstep(0.55, 1.0, hf)[..., None]
    alb = _ramp3(k1, k2, alb0, alb1, alb2) * (0.80 + 0.20 * barb[..., None]) * heat_alb
    hmix = (hf ** 0.9)[..., None]
    base = base * (1 - 0.80 * hmix) + alb * hmix * 0.80
    gold = np.array(gold_rgb)[None, None, :]
    base = base * (1 - spine[..., None] * rib) + gold * spine[..., None] * rib
    # --- 发光：只留最外侧一条细刃口线 ---
    jl = np.clip(1 + (box_blur(rng.random((size, size)).astype(np.float32), 8) - 0.5) * 5.0, 0.65, 1.45)
    wl = line * (0.60 + 0.80 * u) * jl
    lm = sstep(1 - wl, 1 - wl * 0.30, c)
    if shoulder > 0:      # 刃口线内侧一圈很快衰减的暗红“肩”（游戏里 Boss 很小，亚像素细线读不出来，肩部把线撑到 2–3 像素）
        ws = shoulder_w * (0.60 + 0.80 * u) * jl
        lm = np.maximum(lm, sstep(1 - ws, 1 - ws * 0.15, c) ** 1.5 * shoulder)
    lm = lm * sstep(0.05, 0.28, u)
    ku1 = sstep(0.0, 0.50, u)[..., None]
    ku2 = sstep(0.50, 1.0, u)[..., None]
    em = _ramp3(ku1, ku2, deep_rgb, emit_rgb, hot_rgb) * lm[..., None] * line_gain
    hgt = barb * 0.25 + spine * 0.8 - hf * 0.2
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(hgt.astype(np.float32), 1), 2.0)


def blade_maps_r5(emit_rgb, base_rgb, size=1024, seed=23, edge=0.13, heat=0.50, keep=0.42, hot_rgb=(1.0, 0.82, 0.50)):
    """第五轮剑刃（UV 同 ridge_blade：u 沿刃长、v 横跨刃宽，v=0 / 1 为刃口）：暗钢熔缝刃身（只留少量主裂纹发光，
    heat / keep 压低）+ 两侧刃口一道细发光带（暗红 → 橙 → 近金白）；刃身其余部分不发光，刃口留给发光管与火舌。"""
    base, em, nrm = ember_crack_maps(emit_rgb, base_rgb=base_rgb, size=size, seed=seed, cells=5, width=0.026,
                                     fine=0.0, heat=heat, soot=0.45, keep=keep)
    rng = np.random.default_rng(seed + 5)
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    c = np.abs(v - 0.5) * 2
    lick = box_blur(rng.random((size, size)).astype(np.float32), 10)
    wav = 0.5 + 0.5 * np.sin(u * 60.0 + (lick - 0.5) * 18.0)
    w = edge * (0.55 + 0.45 * wav) * (0.6 + 0.4 * sstep(0.0, 0.25, u))
    band = np.clip((c - (1 - w)) / np.maximum(w, 1e-3), 0, 1) ** 1.3
    k2 = sstep(0.5, 1.0, band)[..., None]
    ramp = np.array(emit_rgb)[None, None, :] * (1 - k2) + np.array(hot_rgb)[None, None, :] * k2
    em = np.clip(em + ramp * band[..., None], 0, 1)
    base = base * (1 - 0.6 * band[..., None]) + ramp * band[..., None] * 0.15
    return np.clip(base, 0, 1), em, nrm


def burn_cloth_maps_r5(emit_rgb, base_rgb, line_rgb=None, size=2048, seed=51, buses=14, burn=0.11, reach=(0.30, 0.80)):
    """第五轮燃烧下摆织物：kit 电路纹细线（自下而上渐隐）+ 下摆一道锯齿燃烧线；去掉燃烧线以下整片焦黑区的底光
    （第四轮 char*0.12 是整片发光）与零星余烬点，保持“只有细线发光”。"""
    base, em, nrm = circuit_maps(emit_rgb, base_rgb=base_rgb, line_rgb=line_rgb, size=size, seed=seed, buses=buses,
                                 reach=reach)
    rng = np.random.default_rng(seed + 1)
    v = np.linspace(0, 1, size, dtype=np.float32)[:, None]
    wav = box_blur(rng.random((1, size)).astype(np.float32).repeat(8, axis=0), 12)[0][None, :]
    front = burn * (1 + (wav - 0.5) * 3.0)
    d = v - front
    edge = np.exp(-(d / 0.010) ** 2)
    char = np.clip(-d / 0.05, 0, 1)
    base = base * (1 - 0.75 * char[..., None]) + np.array(emit_rgb)[None, None, :] * edge[..., None] * 0.08
    add = np.clip(edge * 1.1, 0, 1.3)
    em = np.clip(em + np.stack([add * c for c in emit_rgb], axis=2), 0, 1)
    return np.clip(base, 0, 1), em, nrm
