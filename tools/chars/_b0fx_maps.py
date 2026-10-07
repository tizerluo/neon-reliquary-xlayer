"""Boss 0（余烬之王）特效贴图：纯 numpy，不依赖 bpy，可在系统 Python 里单独预览。

火舌 / 火星合并成一张横向图集（同一张图只占一个材质，每根火焰骨只出一个图元）：
    tile 0 / 1 —— 外层火舌 A / B：橙红渐隐，边缘撕裂，尖端被噪声蚀成碎舌
    tile 2     —— 内层炽热细芯：黄白，窄而亮
    tile 3     —— 火星：细长的亮点
每格 TW × TH（u 横向、v 纵向，第 0 行为底 v=0）。每格四周 alpha 都收到 0，格间不会互相渗色。
alpha 与颜色分两张图输出：base（RGB 压暗到 BASE_DIM、alpha 为真实透明度，给 glTF baseColorTexture）、
emit（RGB 全亮，给 emissiveTexture）。这样漫反射部分很暗，火焰靠自发光 + 透明度读出“光”，
不会在游戏的强灯光下被打成一团粉白。
"""

import numpy as np

TILES = 4
TW, TH = 96, 256
BASE_DIM = 0.22


# ===== 噪声 =====
def _smooth(t):
    return t * t * (3 - 2 * t)


def vnoise(rng, h, w, cy, cx):
    """双线性值噪声：纵向 cy 格、横向 cx 格，输出 (h, w)，范围 [0, 1]。"""
    g = rng.random((cy + 2, cx + 2)).astype(np.float32)
    y = np.linspace(0, cy, h, endpoint=False, dtype=np.float32)
    x = np.linspace(0, cx, w, endpoint=False, dtype=np.float32)
    y0, x0 = np.floor(y).astype(int), np.floor(x).astype(int)
    fy, fx = _smooth(y - y0)[:, None], _smooth(x - x0)[None, :]
    a = g[y0][:, x0] * (1 - fx) + g[y0][:, x0 + 1] * fx
    b = g[y0 + 1][:, x0] * (1 - fx) + g[y0 + 1][:, x0 + 1] * fx
    return a * (1 - fy) + b * fy


def fbm(rng, h, w, cy, cx, octaves=4):
    """分形噪声，归一到 [0, 1]。"""
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * vnoise(rng, h, w, cy * 2 ** o, cx * 2 ** o)
        tot += amp
        amp *= 0.5
    out /= tot
    return np.clip((out - out.min()) / max(1e-6, out.max() - out.min()), 0, 1)


def line_noise(rng, h, cells, octaves=3):
    """一维（沿 v）噪声，范围 [0, 1]，用来给左右边缘各做一条独立的撕裂轮廓。"""
    out = np.zeros(h, np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = cells * 2 ** o
        g = rng.random(n + 2).astype(np.float32)
        y = np.linspace(0, n, h, endpoint=False, dtype=np.float32)
        y0 = np.floor(y).astype(int)
        f = _smooth(y - y0)
        out += amp * (g[y0] * (1 - f) + g[y0 + 1] * f)
        tot += amp
        amp *= 0.55
    out /= tot
    return (out - out.min()) / max(1e-6, out.max() - out.min())


def _grid():
    v = np.linspace(0, 1, TH, dtype=np.float32)[:, None] * np.ones((1, TW), np.float32)
    s = (np.linspace(0, 1, TW, dtype=np.float32)[None, :] * 2 - 1) * np.ones((TH, 1), np.float32)
    return v, s


def _ramp(t, c0, c1, c2):
    """三段渐变：t=0 → c0、0.5 → c1、1 → c2。"""
    t = np.clip(t, 0, 1)
    lo = np.clip(t * 2, 0, 1)[..., None]
    hi = np.clip(t * 2 - 1, 0, 1)[..., None]
    c0, c1, c2 = (np.array(c, np.float32)[None, None, :] for c in (c0, c1, c2))
    return (c0 * (1 - lo) + c1 * lo) * (1 - hi) + c2 * hi


# ===== 各格贴图 =====
def envelope(v, peak=0.22, power=0.85):
    """舌形半宽包络（相对半宽 1）：底部略收、约 1/5 高处最宽、向尖端收窄成舌尖。"""
    return (1 - v) ** power * (0.62 + 0.38 * np.sin(np.pi * np.clip(v * 1.4 + peak, 0, 1)))


def outer_tile(seed, hot=0.78, amax=0.64):
    """外层火舌：宽、软、半透明。橙红为主，仅中轴偏黄；左右边缘独立撕裂成舌尖 / 缺口；尖端被噪声蚀成碎舌。"""
    rng = np.random.default_rng(seed)
    v, s = _grid()
    v1 = v[:, 0]
    ax = np.abs(s)
    env = envelope(v)
    # 左右边缘各一条撕裂轮廓：在包络上乘一条沿 v 起伏的噪声
    eL = 1 + 0.75 * (line_noise(rng, TH, 8) - 0.45)
    eR = 1 + 0.75 * (line_noise(rng, TH, 8) - 0.45)
    edge = env * np.where(s < 0, eL[:, None], eR[:, None])
    cover = np.clip((edge - ax) / 0.16, 0, 1)
    # 竖向拉长的湍流（火焰“流纹”）与细碎斑驳
    streak = fbm(rng, TH, TW, 3, 6, 4)
    fleck = fbm(rng, TH, TW, 9, 7, 3)
    # 沿高度蚀刻：尖端先从两侧被吃掉，中轴最后才断开
    g = (1 - v) + 0.30 * (1 - ax) + (fleck - 0.5) * 0.85 * (0.10 + v) + (streak - 0.5) * 0.30
    tip = _smooth(np.clip((g - 0.12) / 0.34, 0, 1))
    rise = np.clip(v / 0.05, 0, 1)
    fade = np.clip((1 - v) / 0.06, 0, 1)
    body = 0.50 + 0.50 * streak
    alpha = np.clip(cover * tip * rise * fade * body * 1.25, 0, 1) * amax
    heat = np.clip((1 - np.clip(ax / np.maximum(env, 0.05), 0, 1) ** 1.3) * (1 - 0.75 * v) * (0.65 + 0.55 * streak),
                   0, 1) * hot
    rgb = _ramp(heat, (0.55, 0.05, 0.012), (1.0, 0.34, 0.045), (1.0, 0.68, 0.20))
    return rgb, alpha


def inner_tile(seed, amax=0.92):
    """内层炽热细芯：窄而亮，黄白，尖端渐隐收束（几何本身也比外层短）。"""
    rng = np.random.default_rng(seed)
    v, s = _grid()
    ax = np.abs(s)
    env = envelope(v, peak=0.30, power=0.95) * 0.92
    eL = 1 + 0.40 * (line_noise(rng, TH, 6) - 0.45)
    eR = 1 + 0.40 * (line_noise(rng, TH, 6) - 0.45)
    edge = env * np.where(s < 0, eL[:, None], eR[:, None])
    cover = np.clip((edge - ax) / 0.20, 0, 1) ** 0.9
    streak = fbm(rng, TH, TW, 3, 4, 3)
    g = (1 - v) * 1.05 + 0.20 * (1 - ax) + (streak - 0.5) * 0.40 * (0.2 + v)
    tip = _smooth(np.clip((g - 0.05) / 0.40, 0, 1))
    rise = np.clip(v / 0.04, 0, 1)
    fade = np.clip((1 - v) / 0.05, 0, 1)
    alpha = np.clip(cover * tip * rise * fade * (0.70 + 0.30 * streak) * 1.20, 0, 1) * amax
    heat = np.clip((1 - np.clip(ax / np.maximum(env, 0.05), 0, 1) ** 1.1) * (1 - 0.50 * v), 0, 1)
    rgb = _ramp(heat, (1.0, 0.45, 0.07), (1.0, 0.80, 0.34), (1.0, 0.97, 0.78))
    return rgb, alpha


def spark_tile(seed, amax=0.95):
    """火星：细长的亮点（竖向菱形），中心近白、两端偏橙。"""
    rng = np.random.default_rng(seed)
    v, s = _grid()
    ax = np.abs(s)
    wv = np.clip(np.sin(np.pi * np.clip(v, 0, 1) ** 0.75), 0, 1) ** 0.9
    cover = np.clip(1 - ax / np.maximum(wv * 0.55, 1e-3), 0, 1) ** 1.4
    alpha = np.clip(cover * (0.85 + 0.15 * fbm(rng, TH, TW, 4, 2, 2)), 0, 1) * amax
    heat = np.clip(cover ** 0.7 * wv, 0, 1)
    rgb = _ramp(heat, (1.0, 0.38, 0.05), (1.0, 0.72, 0.22), (1.0, 0.96, 0.72))
    return rgb, alpha


def atlas(seed=5):
    """拼出图集：返回 (base_rgba, emit_rgb)，行 0 为底。"""
    tiles = [outer_tile(seed * 11 + 1), outer_tile(seed * 11 + 7, hot=0.70), inner_tile(seed * 11 + 3),
             spark_tile(seed * 11 + 5)]
    rgb = np.concatenate([t[0] for t in tiles], axis=1)
    alpha = np.concatenate([t[1] for t in tiles], axis=1)
    base = np.concatenate([rgb * BASE_DIM, alpha[..., None]], axis=2).astype(np.float32)
    return base, rgb.astype(np.float32)


if __name__ == "__main__":
    # 预览：深色背景合成 + 去 alpha 的原图，写到 argv[1]
    import sys
    from PIL import Image
    base, emit = atlas()
    a = base[..., 3:4]
    comp = emit * a * 1.6 + np.array([0.02, 0.02, 0.04], np.float32) * (1 - a)
    big = np.concatenate([np.clip(comp, 0, 1), np.repeat(a, 3, axis=2)], axis=1)
    img = (np.clip(big[::-1], 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img).resize((img.shape[1] * 2, img.shape[0] * 2), Image.NEAREST).save(sys.argv[1])
    print("alpha mean", float(a.mean()), "max", float(a.max()))
