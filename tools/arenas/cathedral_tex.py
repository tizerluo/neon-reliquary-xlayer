"""琉璃大教堂 · 贴图配方（纯 numpy）：彩色玻璃马赛克地砖（可平铺）、地面玫瑰窗纹章、石材（可平铺）。

地砖：12 m × 12 m 一个周期、1024²（≈ 85 像素 / 米）；单元 ≈ 0.6 m 的不规则玻璃片，铅条是细金属线，
局部几条铅条上有发光电路走线（青为主，少量玫红 / 金）。整体偏暗、饱和度克制。
"""

import numpy as np

from . import textures as T

TILE_M = 12.0
STONE_M = 4.0
EMBLEM_R = 15.0
CYAN = "#70bdca"      # 区域主色（游戏给这个区域的环境色）
ROSE = "#d77aa5"
GOLD = "#e0b45a"

# 玻璃色板（sRGB，按“场”的分位数从青 → 蓝 → 靛 → 紫 → 玫红 → 琥珀渐变；偏暗、克制）
GLASS_STOPS = [
    (0.00, "#173f4a"), (0.20, "#1b4d59"), (0.42, "#215b66"), (0.58, "#1e4660"),
    (0.76, "#233a63"), (0.86, "#33336a"), (0.92, "#4a3466"), (0.96, "#612f55"), (1.00, "#6a5329"),
]
LEAD = "#252a31"
SLATE = "#162029"
BRASS = "#6f5c34"


def _gradient(stops, t):
    pos = np.array([s[0] for s in stops])
    cols = np.stack([T.srgb_to_lin(T.hex_rgb(s[1])) for s in stops])
    t = np.clip(t, 0, 1)
    out = np.empty(t.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(t, pos, cols[:, c])
    return out


def _lin(hexcolor):
    return T.srgb_to_lin(T.hex_rgb(hexcolor))


# ===== 地砖 =====
# 发光电路走线不画进贴图（12 m 一周期的贴图里的亮线会铺成整齐的格子），改由 cathedral.py 在每块地砖上用几何随机生成。
FLOOR_SEED, FLOOR_CELLS, FLOOR_JITTER = 11, 20, 0.9


def make_floor(n=1024, seed=FLOOR_SEED, cells=FLOOR_CELLS, mr_size=512):
    """返回 dict：base / normal（uint8 RGB，n×n）、mr（uint8 RGB，mr_size²：G 粗糙度 B 金属度）。
    基础色是“中性偏冷的玻璃明度图”——色相由 cathedral.py 里地面网格的顶点色（低频、不重复）给出，
    所以 12 m 一周期的贴图不会铺出一格一格的色块；单元之间只有很小的色偏。"""
    px_m = TILE_M / n
    vor = T.voronoi_tile(n, cells, FLOOR_JITTER, seed)
    e1m = vor["e1"].astype(np.float64) * TILE_M
    e2m = vor["e2"].astype(np.float64) * TILE_M
    cid = vor["cid"]
    cellr = vor["cell_dist"].astype(np.float64) * TILE_M

    # —— 单元明度 / 色偏 ——
    r_cell = T.rand01(cid, seed, 7)
    lum = 0.16 + 0.34 * T.rand01(cid, seed, 3)              # 线性明度 0.16–0.50（乘顶点色之前）
    tint = np.ones(cid.shape + (3,))
    tint[r_cell < 0.34] = (0.84, 1.0, 1.0)
    tint[(r_cell >= 0.34) & (r_cell < 0.58)] = (0.92, 0.96, 1.0)
    tint[(r_cell >= 0.58) & (r_cell < 0.74)] = (1.0, 0.94, 0.88)
    tint[r_cell >= 0.94] = (1.0, 0.78, 0.62)
    glass = lum[..., None] * tint
    rad = np.clip(cellr / 0.32, 0, 1.2)
    glass *= (1.10 - 0.18 * rad)[..., None]
    glass *= (0.80 + 0.20 * T.smoothstep(0.012, 0.09, e1m))[..., None]
    swirl = T.fbm_periodic(n, seed + 2, beta=1.6, kmin=6, kmax=60)
    glass *= (0.88 + 0.24 * swirl)[..., None]

    # —— 破损单元（约 6%）：更暗，带蛛网状细裂纹 ——
    dmg = T.rand01(cid, seed, 99) < 0.06
    fine = T.voronoi_tile(n, 56, 1.0, seed + 5)
    crack = (fine["e1"].astype(np.float64) * TILE_M < 0.0075) & dmg
    glass = np.where(dmg[..., None], glass * 0.62, glass)
    glass = np.where(crack[..., None], glass * 0.30, glass)

    # —— 铅条 ——
    lead_w = 0.021
    lead_mask = 1.0 - T.smoothstep(lead_w - 0.004, lead_w + 0.004, e1m)
    lead_noise = T.fbm_periodic(n, seed + 3, beta=1.0, kmin=40, kmax=200)
    lead = _lin(LEAD)[None, None, :] * (0.7 + 0.8 * lead_noise)[..., None] * 1.6
    base_lin = glass * (1 - lead_mask[..., None]) + lead * lead_mask[..., None]

    # —— 高度（米）→ 法线 ——
    bevel = T.smoothstep(lead_w * 0.55, lead_w + 0.05, e1m)
    dome = (1.0 - np.clip(cellr / 0.34, 0, 1) ** 2)
    hammer = T.fbm_periodic(n, seed + 6, beta=1.2, kmin=30, kmax=160) - 0.5
    h = 0.0125 * bevel + 0.0035 * dome + 0.0016 * hammer - 0.004 * lead_mask
    h = np.where(crack, h - 0.006, h)
    normal = T.normal_from_height(h, px_m, 1.0)

    # —— 金属度 / 粗糙度（glTF：G = roughness，B = metallic）——
    rough = 0.26 + 0.12 * T.rand01(cid, seed, 41) + 0.12 * swirl
    rough = np.where(dmg, rough + 0.30, rough)
    rough = np.where(lead_mask > 0.5, 0.52, rough)
    metal = np.where(lead_mask > 0.5, 0.85, 0.0)
    mr = np.stack([np.zeros_like(rough), rough, metal], axis=-1)
    k = n // mr_size
    mr = mr.reshape(mr_size, k, mr_size, k, 3).mean(axis=(1, 3))

    return dict(base=T.to_u8(T.lin_to_srgb(base_lin)), normal=normal, mr=T.to_u8(mr), stats={})


# ===== 石材（4 m 周期、512²，可平铺）=====
def make_stone(n=512, seed=21):
    px_m = STONE_M / n
    m1 = T.fbm_periodic(n, seed, beta=2.4, kmin=1, kmax=8)
    m2 = T.fbm_periodic(n, seed + 1, beta=1.0, kmin=14, kmax=110)
    m3 = T.fbm_periodic(n, seed + 3, beta=2.0, kmin=3, kmax=20)
    rid = T.fbm_periodic(n, seed + 5, beta=2.2, kmin=2, kmax=14)      # 脊线噪声：|v-0.5| 小处是一条裂纹
    rmask = T.smoothstep(0.54, 0.70, T.fbm_periodic(n, seed + 7, beta=3.0, kmin=1, kmax=5))
    crack = (1.0 - T.smoothstep(0.003, 0.016, np.abs(rid - 0.5))) * rmask
    lum = 0.40 + 0.07 * (m1 - 0.5) * 2 + 0.05 * (m2 - 0.5) * 2 + 0.035 * (m3 - 0.5) * 2
    lum = lum * (1 - 0.40 * crack)
    tintc = np.array([0.94, 1.0, 1.04])
    base = np.clip(lum[..., None] * tintc[None, None, :], 0, 1)
    moss = T.smoothstep(0.62, 0.8, m3)
    base = base * (1 - 0.14 * moss[..., None]) + np.array([0.02, 0.05, 0.045])[None, None, :] * moss[..., None] * 0.5
    h = 0.008 * (m1 - 0.5) + 0.004 * (m2 - 0.5) + 0.003 * (m3 - 0.5) - 0.006 * crack
    normal = T.normal_from_height(h, px_m, 1.1)
    return dict(base=T.to_u8(base), normal=normal)


# ===== 地面玫瑰窗纹章（30 m 圆形；贴图覆盖 [-15,15]² 米，1024²）=====
def make_emblem(n=1024, seed=31):
    R = EMBLEM_R
    px_m = 2 * R / n
    xs = (np.arange(n) + 0.5) / n * 2 * R - R
    X, Z = np.meshgrid(xs, xs)        # X 向东，Z 向南（行向下）
    r = np.hypot(X, Z)
    th = np.arctan2(Z, X)
    aa = 1.6 * px_m

    def inside(d):                    # 有符号距离（米，内正）→ 抗锯齿遮罩
        return T.smoothstep(-aa, aa, d)

    def line(d, w):                   # 以 d = 0 为中心线、半宽 w 的线
        return 1.0 - T.smoothstep(w - aa, w + aa, np.abs(d))

    # —— 底：与地砖同风格的暗色马赛克 ——
    mv = T.voronoi_tile(n, 30, 0.9, seed)
    e1m = mv["e1"].astype(np.float64) * 2 * R
    mcid = mv["cid"]
    lead_m = 1.0 - T.smoothstep(0.020, 0.032, e1m)

    def tile_color(rgb_hex, var=0.35, seed2=1):
        c = _lin(rgb_hex)[None, None, :] * (1.0 - var / 2 + var * T.rand01(mcid, seed, seed2))[..., None]
        return c * (0.88 + 0.12 * T.smoothstep(0.02, 0.2, e1m))[..., None]

    col = {k: tile_color(v, 0.45, i + 3) for i, (k, v) in enumerate(dict(
        slate=SLATE, teal="#1d5059", blue="#203c62", rose="#5c2d4d", gold="#665027", violet="#33316a").items())}
    img = col["slate"].copy()
    em = np.zeros((n, n))
    em_col = np.zeros((n, n, 3))
    brass = np.zeros((n, n))
    glass_mask = np.zeros((n, n))

    def paint(mask, key):
        nonlocal img
        img = img * (1 - mask[..., None]) + col[key] * mask[..., None]
        glass_mask[:] = np.maximum(glass_mask * (1 - mask), mask)

    # 1) 外圈：齿饰带 r ∈ [13.25, 13.95]，72 段青 / 蓝交替
    band = inside(r - 13.25) * inside(13.95 - r)
    seg = (np.floor((th + np.pi) / (2 * np.pi) * 72).astype(int)) % 2
    paint(band * (seg == 0), "teal")
    paint(band * (seg == 1), "blue")
    sep = line(np.mod((th + np.pi) / (2 * np.pi) * 72 + 0.5, 1.0) - 0.5, 0.045) * band
    brass = np.maximum(brass, sep * 0.6)
    brass = np.maximum(brass, line(r - 14.55, 0.43) + line(r - 13.1, 0.075))
    # 2) 花瓣环：12 瓣，瓣形 w(r) = wmax * sin(πt)^0.65；内含小一号的尖瓣
    ph = np.mod(th + np.pi / 12, np.pi / 6) - np.pi / 12
    petal_id = (np.floor((th + np.pi / 12 + np.pi) / (np.pi / 6)).astype(int)) % 12

    def petal(r_in, r_out, wmax):
        t = np.clip((r - r_in) / (r_out - r_in), 1e-4, 1 - 1e-4)
        s = np.sin(np.pi * t)
        w = wmax * s ** 0.65
        dw = wmax * 0.65 * s ** -0.35 * np.cos(np.pi * t) * np.pi / (r_out - r_in)
        d = (w - np.abs(ph)) * r / np.sqrt(1 + (r * dw) ** 2)
        d = np.where((r > r_in) & (r < r_out), d, -1.0)
        return d

    d_big = petal(7.5, 12.9, 0.235)
    d_small = petal(8.5, 11.9, 0.115)
    big = inside(d_big)
    kind = np.where(petal_id % 3 == 1, 1, 0)
    paint(big * (kind == 0), "teal")
    paint(big * (kind == 1), "blue")
    small = inside(d_small)
    paint(small * (kind == 0), "blue")
    paint(small * (kind == 1), "rose")
    brass = np.maximum(brass, line(d_big, 0.085))
    brass = np.maximum(brass, line(d_small, 0.060) * 0.9)
    # 3) 圆环：12 个圆（落在花瓣之间），半径 1.35，内含金 / 玫红 / 青小圆
    ang_c = (np.arange(12) + 0.5) * np.pi / 6
    rc, rr = 6.2, 1.30
    best_d = np.full((n, n), -9.0)
    best_k = np.zeros((n, n), int)
    for k, a in enumerate(ang_c):
        d = rr - np.hypot(X - rc * np.cos(a), Z - rc * np.sin(a))
        m = d > best_d
        best_d = np.where(m, d, best_d)
        best_k = np.where(m, k, best_k)
    circ = inside(best_d)
    paint(circ * (best_k % 3 == 0), "gold")
    paint(circ * (best_k % 3 == 1), "teal")
    paint(circ * (best_k % 3 == 2), "violet")
    brass = np.maximum(brass, line(best_d, 0.085))
    # 小圆（核心）发光环
    best_in = np.full((n, n), -9.0)
    for k, a in enumerate(ang_c):
        best_in = np.maximum(best_in, 0.55 - np.hypot(X - rc * np.cos(a), Z - rc * np.sin(a)))
    brass = np.maximum(brass, line(best_in, 0.05))
    em_ring = line(best_in, 0.032)
    # 4) 星环：12 尖星，外半径 4.95，内半径 2.9
    star_r = 3.35 + 1.6 * (0.5 + 0.5 * np.cos(12 * th)) ** 1.4
    d_star = (star_r - r) * 0.8
    star = inside(d_star) * inside(r - 2.8)
    paint(star * ((np.floor((th + np.pi) / (np.pi / 6)).astype(int) % 2) == 0), "blue")
    paint(star * ((np.floor((th + np.pi) / (np.pi / 6)).astype(int) % 2) == 1), "teal")
    brass = np.maximum(brass, line(d_star, 0.075) * inside(r - 2.7))
    # 5) 中心：圆盘 r < 2.4，黄铜环 + 青色玻璃 + 电路环 / 节点
    hub = inside(2.4 - r)
    paint(hub, "teal")
    brass = np.maximum(brass, line(r - 2.45, 0.08) + line(r - 1.05, 0.05))
    em_hub = line(r - 1.55, 0.03) * (np.sin(th * 36) > -0.35)
    node = inside(0.34 - r)
    # 辐条节点（每瓣根部一个）
    spokes = np.zeros((n, n))
    for k in range(12):
        a = k * np.pi / 6
        spokes = np.maximum(spokes, inside(0.17 - np.hypot(X - 7.1 * np.cos(a), Z - 7.1 * np.sin(a))))
    em_outer = line(r - 13.1, 0.03) * (np.sin(th * 72) > 0.1)
    em_total = np.clip(em_ring * 0.0 + em_hub + node + spokes * 0.9 + em_outer * 0.8, 0, 1) * 0.55

    # —— 组合：玻璃 + 铅条线（马赛克）+ 黄铜 ——
    leadc = _lin(LEAD)[None, None, :]
    img = img * (1 - 0.8 * lead_m[..., None] * glass_mask[..., None]) + leadc * 0.8 * lead_m[..., None] * glass_mask[..., None]
    swirl = T.fbm_periodic(n, seed + 2, beta=1.6, kmin=8, kmax=80)
    img = img * (0.90 + 0.2 * swirl)[..., None]
    brass_col = _lin(BRASS)[None, None, :] * (0.85 + 0.3 * T.fbm_periodic(n, seed + 3, beta=1.2, kmin=30, kmax=180))[..., None]
    img = img * (1 - brass[..., None]) + brass_col * brass[..., None]
    em_tint = np.where((np.arange(n)[None, :, None] < 0), 0, 1) * _lin(CYAN)[None, None, :]
    emissive_lin = em_tint * em_total[..., None]
    # 外缘：圆外填黑（不会用到）
    outside = (r > R - 0.02)
    img = np.where(outside[..., None], _lin(BRASS)[None, None, :] * 0.5, img)

    # —— 法线：黄铜凸起，玻璃略成圆顶，铅条下凹 ——
    hb = T.blur_periodic(brass, 1.2)
    dome = np.clip(e1m / 0.45, 0, 1)
    h = 0.012 * hb + 0.0035 * dome * glass_mask - 0.004 * lead_m * glass_mask
    h += 0.0012 * (T.fbm_periodic(n, seed + 6, beta=1.2, kmin=30, kmax=160) - 0.5)
    normal = T.normal_from_height(h, px_m, 1.0)
    return dict(base=T.to_u8(T.lin_to_srgb(img)), normal=normal, emissive=T.to_u8(T.lin_to_srgb(emissive_lin)))


if __name__ == "__main__":
    import sys
    import time
    from pathlib import Path
    out = Path(sys.argv[1])
    which = sys.argv[2] if len(sys.argv) > 2 else "floor"
    t = time.time()
    r = dict(floor=make_floor, stone=make_stone, emblem=make_emblem)[which]()
    print(which, time.time() - t, r.get("stats"))
    for k, v in r.items():
        if k != "stats":
            print(k, T.write_png(out / f"{which}_{k}.png", v))
