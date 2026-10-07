"""Boss 4（机械神祇）光束特效贴图：纯 numpy，不依赖 bpy，可在系统 Python 里单独预览。

一张横向图集（同一张图只占一个材质 / 一个图元），每格 TW × TH（u 横向、v 纵向，第 0 行为底 v=0）：
    tile 0 —— 外层光晕：宽、淡、琥珀金，边缘撕裂，带慢速脉冲带
    tile 1 —— 内层光晕：较窄、浅金，叠三股编织的能量丝（正弦蛇行）+ 脉冲带
    tile 2 —— 芯线：很细、白金、最亮，末端渐隐
    tile 3 —— 脉冲环（强）：沿 v 为径向剖面（环带中线最亮），沿 u 为环向（带节点明暗）
    tile 4 —— 脉冲环（弱）：同上，更淡，给束末端用
    tile 5 —— 圆形光晕 / 发射口闪光：以格中心为圆心的归一化圆盘（与格的宽高比无关）
束向的格（0 / 1 / 2）v=0 为炮口、v=1 为束端：头部从零渐入（炮口光球接管），末端渐隐收束。

颜色与透明度分开输出（同 Boss 0 的思路）：
    - 记每个像素“可见亮度” I（0..1）与颜色 C。base 贴图 = (C × BASE_DIM, α = I^0.7)，给 glTF baseColorTexture；
      emit 贴图 = C × I^0.3，给 emissiveTexture。主渲染里 自发光 × α = C × I，亮度由 I 直接决定。
    - emit 预乘了透明度：游戏端的选择性辉光通道把材质换成不透明的 MeshBasicMaterial（只读 emissiveMap、不认 alpha），
      不预乘的话每片薄片的整块矩形都会泛光；预乘后 alpha=0 处自发光为 0，辉光形状与可见形状一致。
漫反射几乎不贡献，光束靠自发光 + 透明度读出“光”，不会被游戏灯光打成一团。
"""

import numpy as np

TILES = 6
TW, TH = 72, 256            # 格内有效宽 / 高
G = 4                          # 格左右各 4 px 的外延（环向格周期延拓，其余格为 0），避免双线性 / mipmap 在格间渗色
CW = TW + 2 * G                # 图集每格实际宽
BASE_DIM = 0.20
GLOW_A, GLOW_B, CORE, RING_A, RING_B, HALO = range(6)


# ===== 噪声 =====
def _smooth(t):
    return t * t * (3 - 2 * t)


def sstep(a, b, x):
    return _smooth(np.clip((x - a) / (b - a), 0, 1))


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


def fbm(rng, h, w, cy, cx, octaves=3):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * vnoise(rng, h, w, cy * 2 ** o, cx * 2 ** o)
        tot += amp
        amp *= 0.5
    out /= tot
    return np.clip((out - out.min()) / max(1e-6, out.max() - out.min()), 0, 1)


def line_noise(rng, h, cells, octaves=3):
    """一维（沿 v）噪声 [0, 1]：给左右边缘各做一条独立的撕裂轮廓。"""
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
    """像素中心坐标：v 为 0..1（自底向顶），s 为 -1..1（格内有效区；外延区 |s|>1）。形状 (TH, CW)。"""
    v = ((np.arange(TH, dtype=np.float32) + 0.5) / TH)[:, None] * np.ones((1, CW), np.float32)
    s = (((np.arange(CW, dtype=np.float32) + 0.5 - G) / TW) * 2 - 1)[None, :] * np.ones((TH, 1), np.float32)
    return v, s


def uv(tile, u, v):
    """图集 UV：tile 为格序号，u / v 为格内 0..1。"""
    return ((tile * CW + G + u * TW) / (TILES * CW), v)


def _ramp(t, c0, c1, c2):
    """三段渐变：t=0 → c0、0.5 → c1、1 → c2。"""
    t = np.clip(t, 0, 1)
    lo = np.clip(t * 2, 0, 1)[..., None]
    hi = np.clip(t * 2 - 1, 0, 1)[..., None]
    c0, c1, c2 = (np.array(c, np.float32)[None, None, :] for c in (c0, c1, c2))
    return (c0 * (1 - lo) + c1 * lo) * (1 - hi) + c2 * hi


def pulse(v, freq, phase=0.0, depth=0.34, sharp=2.0):
    """沿束向的能量脉冲带：freq 个周期，亮带窄、暗带宽。"""
    return (1 - depth) + depth * (0.5 + 0.5 * np.cos(2 * np.pi * (v * freq + phase))) ** sharp * 1.3


def ends(v, head=0.06, tail0=0.42, tail1=1.0, tail_pow=1.0):
    """头部渐入、末端渐隐收束。"""
    return sstep(0.0, head, v) * (1 - sstep(tail0, tail1, v)) ** tail_pow


# ===== 各格贴图：返回 (颜色 rgb, 可见亮度 I) =====
def glow_tile(seed, outer=True):
    """光晕层。outer：宽淡琥珀金；否则较窄浅金并叠三股编织能量丝。"""
    rng = np.random.default_rng(seed)
    v, s = _grid()
    ax = np.abs(s)
    streak = fbm(rng, TH, CW, 12, 3, 3)
    eL = 1 + 0.55 * (line_noise(rng, TH, 9) - 0.5)
    eR = 1 + 0.55 * (line_noise(rng, TH, 9) - 0.5)
    edge = np.where(s < 0, eL[:, None], eR[:, None]) * (0.92 if outer else 0.88)
    xn = ax / np.maximum(edge, 0.2)
    if outer:
        prof = np.exp(-(xn / 0.46) ** 1.7) * np.clip(1 - xn ** 3, 0, 1)
        amp = 0.60
        body = (0.74 + 0.26 * streak) * pulse(v, 6, 0.10, 0.22, 2.0)
        braid = 0.0
    else:
        prof = np.exp(-(xn / 0.40) ** 1.6) * np.clip(1 - xn ** 3, 0, 1)
        amp = 0.62
        body = (0.66 + 0.34 * streak) * pulse(v, 9, 0.35, 0.36, 2.2)
        # 三股编织：沿束向蛇行的细亮丝，相位互错
        braid = 0.0
        for k in range(3):
            c = 0.46 * np.sin(2 * np.pi * (v * 2.4 + k / 3.0 + 0.15 * seed % 1))
            braid = braid + np.exp(-((s - c) / 0.075) ** 2) * (0.55 + 0.45 * np.sin(2 * np.pi * (v * 7 + k * 0.31)) ** 2)
        braid = np.clip(braid, 0, 1) * np.clip(1 - xn ** 2.5, 0, 1)
    I = np.clip((prof * body + braid * (0.55 if not outer else 0)) * ends(v, 0.07, 0.50 if outer else 0.55, 1.0, 1.0) * amp * 1.35, 0, 1)
    heat = np.clip((1 - xn ** 0.8) * (1 - 0.30 * v), 0, 1)
    if outer:
        rgb = _ramp(heat, (1.0, 0.56, 0.16), (1.0, 0.76, 0.32), (1.0, 0.88, 0.52))
    else:
        rgb = _ramp(np.maximum(heat, braid * 0.9), (1.0, 0.72, 0.28), (1.0, 0.87, 0.52), (1.0, 0.96, 0.76))
    return rgb, I


def core_tile(seed):
    """芯线：极细、最亮的白金，沿束向有轻微的明暗起伏，末端渐隐。"""
    rng = np.random.default_rng(seed)
    v, s = _grid()
    ax = np.abs(s)
    flick = 0.88 + 0.12 * fbm(rng, TH, CW, 20, 1, 2)
    prof = np.exp(-(ax / 0.24) ** 1.35) * np.clip(1 - ax ** 3, 0, 1)
    I = np.clip(prof * flick * pulse(v, 9, 0.35, 0.18, 2.0) * ends(v, 0.05, 0.58, 1.0, 1.1) * 1.18, 0, 1)
    heat = np.clip((1 - (ax / 0.45) ** 1.2) * (1 - 0.18 * v), 0, 1)
    rgb = _ramp(heat, (1.0, 0.78, 0.38), (1.0, 0.92, 0.66), (1.0, 0.985, 0.90))
    return rgb, I


def ring_tile(seed, amp):
    """脉冲环：v 为径向（0 内缘 → 1 外缘，中线最亮），u 为环向（整数个周期，首尾无缝），带节点明暗。"""
    rng = np.random.default_rng(seed)
    v, s = _grid()
    u = (s + 1) / 2
    prof = np.exp(-((v - 0.5) / 0.24) ** 2) * np.clip(np.sin(np.pi * np.clip(v, 0, 1)), 0, 1) ** 0.5
    nodes = 0.74 + 0.26 * (0.5 + 0.5 * np.cos(2 * np.pi * (u * 5 + 0.1 * seed)))
    jag = 0.86 + 0.14 * np.cos(2 * np.pi * (u * 13 + 0.7))
    I = np.clip(prof * nodes * jag * amp, 0, 1)
    heat = np.clip(np.exp(-((v - 0.5) / 0.14) ** 2), 0, 1)
    rgb = _ramp(heat, (1.0, 0.64, 0.22), (1.0, 0.82, 0.42), (1.0, 0.95, 0.74))
    return rgb, I


def halo_tile(seed, amp=0.95):
    """圆形光晕 / 炮口闪光：归一化圆盘（r<1），亮芯 + 宽软晕 + 一圈淡淡的光环，边缘零。"""
    v, s = _grid()
    x, y = s, v * 2 - 1
    r = np.sqrt(x * x + y * y)
    core = np.exp(-(r / 0.26) ** 2)
    soft = np.exp(-(r / 0.62) ** 1.4) * 0.62
    ring = 0.26 * np.exp(-((r - 0.66) / 0.07) ** 2)
    I = np.clip((core + soft + ring) * (1 - sstep(0.62, 1.0, r)) * amp, 0, 1)
    heat = np.clip(1 - r / 0.7, 0, 1)
    rgb = _ramp(heat, (1.0, 0.64, 0.22), (1.0, 0.84, 0.46), (1.0, 0.97, 0.82))
    return rgb, I


def atlas(seed=4):
    """拼出图集：返回 (base_rgba, emit_rgb)，行 0 为底。"""
    tiles = [glow_tile(seed * 7 + 1, outer=True), glow_tile(seed * 7 + 2, outer=False), core_tile(seed * 7 + 3),
             ring_tile(seed * 7 + 4, 0.85), ring_tile(seed * 7 + 5, 0.50), halo_tile(seed * 7 + 6)]
    rgb = np.concatenate([t[0] for t in tiles], axis=1)
    I = np.concatenate([t[1] for t in tiles], axis=1)
    alpha = np.clip(I, 0, 1) ** 0.7
    emit = rgb * (np.clip(I, 0, 1) ** 0.3)[..., None]
    base = np.concatenate([rgb * BASE_DIM, alpha[..., None]], axis=2).astype(np.float32)
    return base, emit.astype(np.float32)


if __name__ == "__main__":
    # 预览：深色背景合成 + 每格的 alpha，写到 argv[1]
    import sys
    from PIL import Image
    base, emit = atlas()
    a = base[..., 3:4]
    comp = emit * a * 2.4 + np.array([0.02, 0.02, 0.04], np.float32) * (1 - a)
    big = np.concatenate([np.clip(comp, 0, 1), np.repeat(a, 3, axis=2)], axis=1)
    img = (np.clip(big[::-1], 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img).resize((img.shape[1] * 2, img.shape[0] * 2), Image.NEAREST).save(sys.argv[1])
    print("alpha mean", float(a.mean()), "max", float(a.max()), "size", base.shape)
