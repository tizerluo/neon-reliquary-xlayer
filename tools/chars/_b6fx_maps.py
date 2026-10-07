"""Boss 6（剧毒三位体）毒雾特效贴图：纯 numpy，不依赖 bpy，可在系统 Python 里单独预览。

做法同 Boss 4（_b4fx_maps）：一张横向图集（一个材质 / 一个图元），每格 TW × TH（u 横向、v 纵向，第 0 行为底 v=0）。
毒雾沿 v 从喷口（v=0）向雾梢（v=1）发展：根部浓、热、窄，向外扩散变淡变宽，雾梢湍流撕碎渐隐。
    tile 0 —— 外层雾壳（环向周期可平铺）：深翠绿、宽大的湍流斑驳（域扭曲的分形噪声），整体偏淡
    tile 1 —— 内层雾壳（环向周期）：更亮的毒绿，沿喷流方向拉长的螺旋丝状纹
    tile 2 —— 喷流芯壳（环向周期）：很窄、近喷口最亮的浅青柠色细长条纹，约 60% 束长处渐隐
    tile 3 —— 宽雾片（穿过雾轴的平面片）：中线最浓、两侧撕裂渐隐，带孔洞状斑驳
    tile 4 —— 窄雾片：较窄较亮，沿流向的细丝纹
    tile 5 —— 毒滴：水滴形（头圆尾尖，v=1 为前进方向的圆头），亮缘 + 高光 + 半透明体
    tile 6 —— 喷口光晕：以格中心为圆心的归一化圆盘（喷口处一小团亮雾）

颜色与透明度分开输出（同 Boss 4）：记每像素“可见亮度” I（0..1）与颜色 C。
    base 贴图 = (C × BASE_DIM, α = I^0.7)，给 glTF baseColorTexture；
    emit 贴图 = C × I^0.3（预乘透明度：游戏端选择性辉光通道只读 emissiveMap、不认 alpha，
    不预乘的话每片薄片的整块矩形都会泛光；预乘后 alpha=0 处自发光为 0，辉光形状与可见形状一致）。
主渲染里 自发光 × α = C × I，亮度由 I 直接决定；漫反射几乎不贡献，毒雾靠自发光 + 透明度读出“雾”。
环向周期格（0 / 1 / 2）的左右外延区按周期延拓（噪声在 u 方向周期），其余格外延区由 EXTEND 取边缘。
"""

import numpy as np

TILES = 7
TW, TH = 64, 256            # 格内有效宽 / 高
G = 4                          # 格左右各 4 px 外延，避免双线性 / mipmap 在格间渗色
CW = TW + 2 * G                # 图集每格实际宽（7 × 72 = 504 < 512：游戏版导出不会被减半）
BASE_DIM = 0.18
MIST_A, MIST_B, JET, BILLOW_A, BILLOW_B, DROP, HALO = range(7)


# ===== 噪声（横向周期值噪声；纵向夹紧） =====
def _smooth(t):
    return t * t * (3 - 2 * t)


def sstep(a, b, x):
    return _smooth(np.clip((x - a) / (b - a), 0, 1))


def vnoise_at(g, Y, X):
    """在任意坐标 (Y, X) 处采样值噪声网格 g（ny, nx）；X 以 nx 为周期，Y 夹紧到网格内。"""
    ny, nx = g.shape
    Y = np.clip(Y, 0, ny - 1.001)
    y0 = np.floor(Y).astype(int)
    fy = _smooth(Y - y0)
    xf = np.floor(X)
    fx = _smooth(X - xf)
    x0 = xf.astype(int) % nx
    x1 = (x0 + 1) % nx
    a = g[y0, x0] * (1 - fx) + g[y0, x1] * fx
    b = g[y0 + 1, x0] * (1 - fx) + g[y0 + 1, x1] * fx
    return (a * (1 - fy) + b * fy).astype(np.float32)


def fbm_at(rng, Y, X, cy, cx, octaves=3, gain=0.52):
    """分形噪声：纵向 cy 格、横向 cx 格（X 周期为 cx），输出约 [0, 1] 并做固定对比拉伸（不依赖数组范围，周期延拓才无缝）。"""
    out = np.zeros(np.shape(Y), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        k = 2 ** o
        g = rng.random((cy * k + 2, cx * k)).astype(np.float32)
        out += amp * vnoise_at(g, Y * k, X * k)
        tot += amp
        amp *= gain
    out /= tot
    return np.clip((out - 0.5) * 2.3 + 0.5, 0, 1)


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


# 毒绿色阶：深翠绿 → 毒绿 → 浅青柠（中间不过白，保持“绿”）
EMERALD, TOXIC, LIME = (0.02, 0.46, 0.22), (0.20, 0.94, 0.34), (0.62, 1.0, 0.36)


def _warp(rng, Y, X, cy, cx, amt_y, amt_x):
    """域扭曲：用两张低频噪声把采样坐标搅动，得到卷曲的湍流斑驳。"""
    wy = fbm_at(rng, Y, X, cy, cx, 2) - 0.5
    wx = fbm_at(rng, Y + 7.3, X + 3.1, cy, cx, 2) - 0.5
    return Y + wy * amt_y, X + wx * amt_x


# ===== 各格：返回 (颜色 rgb, 可见亮度 I) =====
def mist_tile(seed, inner):
    """环向周期的雾壳。外层：宽大斑驳、偏淡；内层：沿流向拉长的螺旋丝，更亮。"""
    rng = np.random.default_rng(seed)
    v, s = _grid()
    u = (s + 1) / 2
    if not inner:
        cx, cy = 4, 3
        Y, X = _warp(rng, v * cy, u * cx, cy, cx, 1.1, 1.6)
        D = fbm_at(rng, Y, X, cy, cx, 4)
        blot = sstep(0.34, 0.80, D)
        body = 0.10 + 0.90 * blot
        amp = 0.30
        env = sstep(0.02, 0.24, v) * (1 - sstep(0.34, 1.0, v)) ** 1.15
    else:
        cx, cy = 6, 2
        # 螺旋丝：相位随 v 推进，丝宽沿流向拉长
        Y, X = _warp(rng, v * cy, u * cx + v * 1.6, cy, cx, 0.7, 1.3)
        D = fbm_at(rng, Y, X, cy, cx, 3)
        strand = np.exp(-((np.abs(np.sin(np.pi * (X * 1.0 + 0.2 * D))) - 0.0) / 0.34) ** 1.5)
        blot = np.clip(0.55 * sstep(0.30, 0.85, D) + 0.60 * strand * (0.5 + 0.5 * D), 0, 1)
        body = 0.12 + 0.88 * blot
        amp = 0.40
        env = sstep(0.02, 0.22, v) * (1 - sstep(0.36, 0.96, v)) ** 1.15
    I = np.clip(body * env * amp * 1.45, 0, 1)
    heat = np.clip(0.18 + 0.85 * blot - 0.35 * v, 0, 1)
    rgb = _ramp(heat, EMERALD, TOXIC, LIME)
    return rgb, I


def jet_tile(seed):
    """喷流芯壳（环向周期）：很窄的快速流线，近喷口最亮，向雾梢拉丝渐隐。"""
    rng = np.random.default_rng(seed)
    v, s = _grid()
    u = (s + 1) / 2
    cx, cy = 10, 2
    Y, X = _warp(rng, v * cy, u * cx, cy, cx, 0.5, 0.8)
    D = fbm_at(rng, Y, X, cy, cx, 3)
    streak = sstep(0.28, 0.80, D)
    env = sstep(0.0, 0.04, v) * (1 - sstep(0.12, 0.66, v)) ** 1.3
    I = np.clip((0.35 + 0.65 * streak) * env * 1.05, 0, 1)
    heat = np.clip(0.55 + 0.5 * streak - 0.5 * v, 0, 1)
    rgb = _ramp(heat, TOXIC, LIME, (0.92, 1.0, 0.78))
    return rgb, I


def billow_tile(seed, narrow):
    """穿过雾轴的平面片：中线最浓、两侧撕裂渐隐，带孔洞状斑驳。narrow 为窄亮片（沿流向的细丝）。"""
    rng = np.random.default_rng(seed)
    v, s = _grid()
    ax = np.abs(s)
    eL = 1 + 0.85 * (line_noise(rng, TH, 9) - 0.5)
    eR = 1 + 0.85 * (line_noise(rng, TH, 9) - 0.5)
    edge = np.where(s < 0, eL[:, None], eR[:, None]) * (0.90 if not narrow else 0.84)
    xn = ax / np.maximum(edge, 0.2)
    u = (s + 1) / 2
    if not narrow:
        prof = np.exp(-(xn / 0.74) ** 1.8) * np.clip(1 - xn ** 3, 0, 1)
        cx, cy = 3, 6
        Y, X = _warp(rng, v * cy, u * cx + 1.0, cy, cx + 1, 1.0, 1.0)
        D = fbm_at(rng, Y, X, cy, cx + 1, 4)
        body = 0.06 + 0.94 * sstep(0.36, 0.80, D)
        amp = 0.34
        env = sstep(0.02, 0.24, v) * (1 - sstep(0.34, 1.0, v)) ** 1.15
        heat = np.clip((1 - xn ** 0.9) * 0.70 - 0.26 * v + 0.45 * D - 0.10, 0, 1)
        rgb = _ramp(heat, EMERALD, TOXIC, LIME)
    else:
        prof = np.exp(-(xn / 0.42) ** 1.6) * np.clip(1 - xn ** 3, 0, 1)
        cx, cy = 5, 2
        Y, X = _warp(rng, v * cy, u * cx + 1.0, cy, cx + 1, 0.8, 1.2)
        D = fbm_at(rng, Y, X, cy, cx + 1, 3)
        # 沿流向的细丝：丝心随 v 蛇行
        c = 0.30 * np.sin(2 * np.pi * (v * 1.7 + 0.15 * seed % 1))
        thread = np.exp(-((s - c) / 0.17) ** 2) * (0.5 + 0.5 * np.sin(2 * np.pi * (v * 5.5 + 0.3 * D)) ** 2)
        body = np.clip(0.28 + 0.52 * sstep(0.30, 0.85, D) + 0.55 * thread, 0, 1)
        amp = 0.50
        env = sstep(0.0, 0.14, v) * (1 - sstep(0.30, 0.90, v)) ** 1.2
        heat = np.clip((1 - xn ** 0.8) * 0.8 + 0.4 * thread - 0.30 * v, 0, 1)
        rgb = _ramp(heat, TOXIC, LIME, (0.90, 1.0, 0.76))
    I = np.clip(prof * body * env * amp * 1.45, 0, 1)
    return rgb, I


def drop_tile(seed):
    """毒滴：水滴形，圆头朝前（v=1 方向为前进方向，圆头圆心在 v≈0.68），尖尾拖向 v≈0.06。
    亮缘 + 半透明体 + 左上高光点，半透明亮绿。几何四边形按 长:宽 ≈ 1.7:1 取，圆头才是正圆。"""
    v, s = _grid()
    vc, rs, rv = 0.68, 0.86, 0.26      # 圆头圆心（v）与椭圆半轴（s 向 / v 向）；长宽比 1.7 时折算为正圆
    head = np.sqrt((s / rs) ** 2 + ((v - vc) / rv) ** 2)
    t = np.clip((v - 0.06) / (vc - 0.06), 0, 1)
    tail_in = np.abs(s) / np.maximum(rs * t ** 1.5, 1e-3)
    inside = np.where(v >= vc, head, tail_in)
    sil = 1 - sstep(0.78, 1.0, inside)
    rim = np.exp(-((inside - 0.86) / 0.14) ** 2)
    body = 0.30 + 0.36 * (1 - np.clip(inside, 0, 1) ** 2)
    # 高光：靠头部左上
    hx, hy = (s + 0.38) / 0.26, (v - vc - 0.12) / 0.075
    spec = np.exp(-(hx * hx + hy * hy) * 1.1)
    I = np.clip((body + 0.50 * rim) * sil * 0.82 + 0.50 * spec * sil, 0, 1)
    heat = np.clip(0.42 + 0.30 * rim + 0.55 * spec, 0, 1)
    rgb = _ramp(heat, EMERALD, TOXIC, (0.88, 1.0, 0.80))
    return rgb, I


def halo_tile(seed, amp=0.85):
    """喷口光晕：归一化圆盘（r<1），亮芯 + 宽软晕，边缘零。"""
    v, s = _grid()
    x, y = s, v * 2 - 1
    r = np.sqrt(x * x + y * y)
    core = np.exp(-(r / 0.28) ** 2)
    soft = np.exp(-(r / 0.60) ** 1.4) * 0.60
    I = np.clip((core + soft) * (1 - sstep(0.62, 1.0, r)) * amp, 0, 1)
    heat = np.clip(1 - r / 0.75, 0, 1)
    rgb = _ramp(heat, EMERALD, TOXIC, LIME)
    return rgb, I


def atlas(seed=6):
    """拼出图集：返回 (base_rgba, emit_rgb)，行 0 为底。"""
    tiles = [mist_tile(seed * 11 + 1, False), mist_tile(seed * 11 + 2, True), jet_tile(seed * 11 + 3),
             billow_tile(seed * 11 + 4, False), billow_tile(seed * 11 + 5, True), drop_tile(seed * 11 + 6),
             halo_tile(seed * 11 + 7)]
    rgb = np.concatenate([t[0] for t in tiles], axis=1)
    I = np.concatenate([t[1] for t in tiles], axis=1)
    alpha = np.clip(I, 0, 1) ** 0.7
    emit = rgb * (np.clip(I, 0, 1) ** 0.3)[..., None]
    base = np.concatenate([rgb * BASE_DIM, alpha[..., None]], axis=2).astype(np.float32)
    return base, emit.astype(np.float32)


if __name__ == "__main__":
    # 预览：深色背景合成（强度 2.4）+ 每格的 alpha，写到 argv[1]
    import sys
    from PIL import Image
    base, emit = atlas()
    a = base[..., 3:4]
    comp = emit * a * 2.4 + np.array([0.02, 0.025, 0.03], np.float32) * (1 - a)
    big = np.concatenate([np.clip(comp, 0, 1), np.repeat(a, 3, axis=2)], axis=1)
    img = (np.clip(big[::-1], 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img).resize((img.shape[1] * 2, img.shape[0] * 2), Image.NEAREST).save(sys.argv[1])
    print("alpha mean", float(a.mean()), "max", float(a.max()), "size", base.shape)
