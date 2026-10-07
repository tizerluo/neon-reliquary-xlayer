"""冰封档案馆 · 贴图配方（纯 numpy）：冰板地面（可平铺）、冰下星盘纹章、冻石（可平铺）、书架墙（可平铺）、冰壳法线（可平铺）。

地面（r2 重做）：20 m × 20 m 一个周期、1024²（≈ 51 像素 / 米）；约 4 m 的大冰板，接缝是被位移场弯曲 / 带毛刺的霜白破裂边（宽窄变化、宽处中心有暗缝、两侧一圈霜）；
厚冰：板心深蓝黑、靠缝浅白，加生长纹 / 浑浊 / 冻裂纹网（浅深两层）/ 蛛网冲击裂纹 / 气泡串；
冰下封着书 / 摊开的书 / 卷轴筒 / 圣物匣 / 散页（每个周期 15 簇，三个深度层各自模糊并向冰色淡出，比接缝对比低）；
法线 = 接缝倒角 + 崩口 + 裂纹沟 + 每块板各自的倾斜（只有 2 块带高光，让轮廓光扫出一片冷色高光）；粗糙度：清冰 ≈ 0.24–0.31，霜 / 缝更高。
基础色是“相对冰色”的明度图，绝对明暗 / 色相由 archive.py 里地面网格的顶点色（低频、不重复）+ UV 位移（uv_warp）给出，所以贴图不会铺出整齐的格子。
所有颜色偏暗、饱和度低（钢蓝），冰的质感靠法线、粗糙度、厚冰深浅和冰下物件，不靠提亮。纹章与地面共用同一套 _ice_surface。
"""

import math

import numpy as np

from . import textures as T

TILE_M = 20.0
FLOOR_SEED, FLOOR_CELLS, FLOOR_JITTER = 41, 5, 0.85
EMBLEM_R = 15.0
STONE_M = 4.0
SHELF_M = 4.0
ICE_M = 3.0
MOOD = "#9ab7dd"


def _lin(hexcolor):
    return T.srgb_to_lin(T.hex_rgb(hexcolor))


def _wrap(d):
    """环面上的最短差（周期单位）。"""
    return (d + 0.5) % 1.0 - 0.5


# =====================================================================
# 局部窗口“盖章”：在 n×n 环面数组里只算物体周围的小窗口（越界回绕）
# =====================================================================
class Layer:
    def __init__(self, n, tile_m):
        self.n, self.tile_m = n, tile_m
        self.a = np.zeros((n, n), np.float32)

    def stamp(self, cx, cy, half_m, fn):
        """(cx, cy)：周期单位坐标（cx 向右 = 东，cy 向下 = 南）；fn(dx, dy) 收到局部米坐标网格（dx 东、dy 南），返回 0..1。"""
        n = self.n
        px = self.tile_m / n
        W = min(int(math.ceil(half_m / px)) + 2, n // 2 - 1)
        ci, cj = int(round(cx * n - 0.5)), int(round(cy * n - 0.5))
        idx = np.arange(-W, W + 1)
        ii, jj = (ci + idx) % n, (cj + idx) % n
        dx = np.tile((idx * px)[None, :], (2 * W + 1, 1))
        dy = np.tile((idx * px)[:, None], (1, 2 * W + 1))
        v = fn(dx, dy)
        sl = np.ix_(jj, ii)
        self.a[sl] = np.maximum(self.a[sl], v.astype(np.float32))


def _rot(dx, dy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return dx * c + dy * s, -dx * s + dy * c


def _rect(u, v, hw, hh, aa=0.006):
    d = np.maximum(np.abs(u) - hw, np.abs(v) - hh)
    return 1.0 - T.smoothstep(-aa, aa, d)


def _line_mask(u, v, hw, aa=0.006):
    return 1.0 - T.smoothstep(hw - aa, hw + aa, np.abs(v))


# =====================================================================
# 通用小工具（环面上的场 / 位移 / 查表）
# =====================================================================
def _gauss(n, seed, kmin, kmax, beta=2.0):
    """零均值、标准差 ≈ 1 的可平铺噪声（kmin / kmax：每个周期内的频率）。"""
    return (T.fbm_periodic(n, seed, beta=beta, kmin=kmin, kmax=kmax) - 0.5) * 4.0


def _grid(n):
    xs = (np.arange(n) + 0.5) / n
    return np.meshgrid(xs, xs)                 # X 向东（列），Y 向南（行）


def _lookup(a, wx, wy, tile_m, nearest=False):
    """在“位移后的坐标”上取值：out(p) = a(p + w(p))；wx / wy 单位米。整数场（板编号）用最近邻。"""
    n = a.shape[0]
    X, Y = _grid(n)
    x, y = X + wx / tile_m, Y + wy / tile_m
    if nearest:
        return a[np.floor((y % 1.0) * n).astype(int) % n, np.floor((x % 1.0) * n).astype(int) % n]
    return T.sample_periodic(a, x, y)


WARP_LOW = 0.15          # 接缝整体弯曲的位移标准差（米）；符文引导线也按同一个场偏移，才贴得住缝


def warp_low(n=1024, seed=FLOOR_SEED):
    """低频位移场（米）：让直的沃罗诺伊边弯成冰板破裂的样子。archive.py 里的符文线用同一个场（采样 sample_periodic）。"""
    return WARP_LOW * _gauss(n, seed + 101, 2, 7), WARP_LOW * _gauss(n, seed + 102, 2, 7)


UVW = ((0.90, 0.0173, 0.0111, 0.7), (0.45, -0.0127, 0.0243, 2.1), (0.22, 0.039, 0.027, 4.0),
       (0.90, -0.0131, 0.0187, 3.9), (0.45, 0.0229, 0.0121, 1.2), (0.22, 0.031, -0.041, 5.5))


def uv_warp(x, z):
    """世界坐标 (x, z)（米）→ 地面贴图坐标的位移 (dx, dz)（米）：平滑、低频、不周期的几组正弦。
    贴图坐标 = 世界坐标 + 位移 → 20 m 周期的贴图在世界里不会铺成整齐的格子（每一份拷贝的位置 / 朝向都略有不同；最大拉伸约 ±10%）。
    archive.py 里地面网格的 UV 和符文引导线都用它。"""
    x, z = np.asarray(x, dtype=np.float64), np.asarray(z, dtype=np.float64)
    out = []
    for k in (0, 3):
        out.append(sum(a * np.sin(math.tau * (fx * x + fz * z) + ph) for a, fx, fz, ph in UVW[k:k + 3]))
    return out[0], out[1]


def _smooth_over(base, color, alpha):
    """base (n,n,3) 之上叠 color（(3,) 或 (n,n,3)），alpha (n,n)。"""
    a = np.clip(alpha, 0.0, 1.0)[..., None]
    return base * (1.0 - a) + np.asarray(color, dtype=np.float64) * a


def _blur3(a, r):
    return np.stack([T.blur_periodic(a[..., k], r) for k in range(3)], axis=-1)


# =====================================================================
# 冰下物件：俯视，物件局部米坐标（u 向东、v 向南），每个绘制函数返回 (alpha, 预乘 RGB)
# 颜色是“相对冰色”的线性值（冰板中值 ≈ 0.25）；纸 ≈ 冰的 2 倍亮，皮革 / 木 ≈ 冰的一半，褪色金偏暖小面积
# =====================================================================
PAPER = np.array([1.08, 0.90, 0.60])
INK = np.array([0.20, 0.17, 0.13])
GOLD = np.array([1.10, 0.80, 0.32])
WOOD = np.array([0.22, 0.155, 0.105])
LEATHERS = [np.array(c) for c in ((0.46, 0.25, 0.14), (0.36, 0.31, 0.20), (0.40, 0.18, 0.15), (0.24, 0.34, 0.25), (0.34, 0.29, 0.26))]
AA = 0.010


class _Cv:
    """小画布：预乘 alpha 的 over 叠加。"""

    def __init__(self, shape):
        self.a = np.zeros(shape)
        self.c = np.zeros(shape + (3,))

    def put(self, mask, color, k=1.0):
        m = np.clip(mask * k, 0.0, 1.0)
        self.c = self.c * (1.0 - m[..., None]) + np.asarray(color, dtype=np.float64) * m[..., None]
        self.a = self.a + m * (1.0 - self.a)

    def out(self):
        return self.a, self.c


def _cov(d, aa=AA):
    return 1.0 - T.smoothstep(-aa, aa, d)


def _box_d(u, v, hw, hh):
    return np.maximum(np.abs(u) - hw, np.abs(v) - hh)


def _rbox_d(u, v, hw, hh, r):
    qx, qy = np.abs(u) - (hw - r), np.abs(v) - (hh - r)
    return np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0)) + np.minimum(np.maximum(qx, qy), 0.0) - r


def _stripes(v, pitch, duty):
    return T.smoothstep(0.5 - duty, 0.5 - duty + 0.30, 0.5 + 0.5 * np.cos(v / pitch * math.tau))


def paint_page(u, v, w, h, paper, skew=0.0, fold=True):
    cv = _Cv(u.shape)
    u2 = u - skew * v
    body = _cov(_box_d(u2, v, w / 2, h / 2))
    shade = 0.84 + 0.26 * np.clip(0.5 + u2 / w * 0.9, 0.0, 1.0)
    cv.put(body, paper[None, None, :] * shade[..., None])
    txt = _cov(_box_d(u2, v, w / 2 - 0.05, h / 2 - 0.07)) * _stripes(v, 0.052, 0.20)
    cv.put(txt * body, paper * 0.36, 0.75)
    if fold:
        tri = ((u2 + v) > (w / 2 + h / 2 - 0.17)) * body
        cv.put(tri, paper * 0.62)
        cv.put(tri * (1 - _cov(np.abs((u2 + v) - (w / 2 + h / 2 - 0.17)) - 0.010)), paper * 1.15)
    rim = body * (1 - _cov(_box_d(u2, v, w / 2 - 0.016, h / 2 - 0.016)))
    cv.put(rim, paper * 0.52, 0.7)
    return cv.out()


def paint_open_book(u, v, W, H, leather):
    """摊开的书：两页（各 W 宽）+ 书脊折线 + 外圈封皮边。页面比冰亮，向书脊处变暗（页心下陷）。"""
    cv = _Cv(u.shape)
    cv.put(_cov(_rbox_d(u, v, W + 0.075, H / 2 + 0.075, 0.04)), leather)
    cv.put(_cov(_rbox_d(u, v, W + 0.075 - 0.014, H / 2 + 0.075 - 0.014, 0.03)) * (1 - _cov(_rbox_d(u, v, W + 0.075 - 0.032, H / 2 + 0.075 - 0.032, 0.025))), leather * 1.8, 0.8)
    for sgn in (-1, 1):
        uu = u - sgn * (W / 2 + 0.003)
        page = _cov(_box_d(uu, v, W / 2 - 0.006, H / 2))
        t = np.clip(np.abs(u) / W, 0.0, 1.0)
        shade = 0.58 + 0.42 * T.smoothstep(0.0, 0.92, t) + 0.10 * T.smoothstep(0.80, 1.0, t)
        cv.put(page, PAPER[None, None, :] * shade[..., None])
        txt = _cov(_box_d(uu, v, W / 2 - 0.075, H / 2 - 0.09)) * _stripes(v, 0.054, 0.21)
        cv.put(txt * page, PAPER * 0.34, 0.8)
        cv.put(_cov(_box_d(uu, v + H * 0.30, W * 0.18, 0.045)) * page, PAPER * 0.45, 0.7)         # 插图 / 标题块
        ring = page * (1 - _cov(_box_d(uu, v, W / 2 - 0.032, H / 2 - 0.022)))
        cv.put(ring, PAPER * 0.52, 0.65)                                                          # 书页叠边的暗线
    cv.put(_cov(_box_d(u, v, 0.024, H / 2 + 0.005)), (0.05, 0.04, 0.034), 0.95)                     # 书脊折线
    cv.put(_cov(_box_d(u, v, 0.075, H / 2)) * 0.5, (0.07, 0.058, 0.046))                            # 折线两侧的下陷阴影
    return cv.out()


def paint_scroll(u, v, L, R):
    """卷轴筒：卷起的纸（圆柱明暗）+ 束带 + 两端的圆盘端盖（带金心）+ 杆头。"""
    cv = _Cv(u.shape)
    body = _cov(_box_d(u, v, L / 2, R))
    s = np.sqrt(np.clip(1.0 - ((v + 0.22 * R) / R) ** 2, 0.0, 1.0))
    cv.put(body, PAPER[None, None, :] * (0.40 + 0.62 * s)[..., None])
    for k in (-1, 1):
        cv.put(body * _cov(np.abs(u - k * (L / 2 - 0.10)) - 0.006) * 0.6, PAPER * 0.45)          # 纸卷的层线
    for pos in (-0.30 * L, 0.18 * L):
        cv.put(_cov(_box_d(u - pos, v, 0.020, R + 0.012)), GOLD * 0.62)
    for k in (-1, 1):
        cv.put(_cov(_box_d(u - k * (L / 2 + 0.014), v, 0.030, R + 0.065)), WOOD * 1.3)            # 端盖（侧视的圆盘）
        cv.put(_cov(_box_d(u - k * (L / 2 + 0.014), v, 0.011, R + 0.050)), GOLD * 0.8)
        cv.put(_cov(_box_d(u - k * (L / 2 + 0.085), v, 0.05, 0.030)), WOOD)                        # 杆
        cx = L / 2 + 0.19
        cv.put(_cov(np.hypot(u - k * cx, v) - 0.105), WOOD * 1.25)                                  # 圆形杆头
        cv.put(_cov(np.hypot(u - k * cx, v) - 0.070), GOLD * 0.55)
        cv.put(_cov(np.hypot(u - k * cx, v) - 0.030), GOLD * 1.05)
    return cv.out()


def paint_casket(u, v, W, H):
    """圣物匣：方盒 + 内缩盖板 + 盖线（合页）+ 两道带 + 四个包角（褪色金）+ 锁扣。"""
    cv = _Cv(u.shape)
    cv.put(_cov(_rbox_d(u, v, W / 2, H / 2, 0.035)), WOOD)
    panel = _cov(_rbox_d(u, v, W / 2 - 0.07, H / 2 - 0.07, 0.02))
    grad = 1.0 + 0.45 * np.clip(-u / W - v / H, -0.5, 0.5)
    cv.put(panel, WOOD[None, None, :] * (2.0 * grad)[..., None])
    cv.put(_cov(_box_d(u, v + H * 0.20, W / 2, 0.011)), (0.035, 0.028, 0.026), 0.95)               # 盖线
    for pos in (-0.30 * W, 0.30 * W):
        cv.put(_cov(_box_d(u - pos, v, 0.040, H / 2)), GOLD * 0.62)                                 # 包带
    for sx in (-1, 1):
        for sy in (-1, 1):
            a1 = _cov(_box_d(u - sx * (W / 2 - 0.15), v - sy * (H / 2 - 0.045), 0.15, 0.045))
            a2 = _cov(_box_d(u - sx * (W / 2 - 0.045), v - sy * (H / 2 - 0.15), 0.045, 0.15))
            cv.put(np.maximum(a1, a2), GOLD)
    cv.put(_cov(_rbox_d(u, v - (H / 2 - 0.09), 0.085, 0.105, 0.015)), GOLD * 1.15)                 # 锁扣
    cv.put(_cov(np.hypot(u, v - (H / 2 - 0.09)) - 0.022), (0.05, 0.038, 0.03))
    return cv.out()


def paint_book(u, v, w, h, leather):
    """合上的书：封皮 + 书脊（竖脊 + 金色横脊）+ 内框线 + 书名牌。"""
    cv = _Cv(u.shape)
    cv.put(_cov(_rbox_d(u, v, w / 2, h / 2, 0.018)), leather)
    cv.put(_cov(_box_d(u + w / 2 - 0.05, v, 0.05, h / 2)), leather * 0.55)
    for k in range(4):
        y = -h / 2 + h * (k + 1) / 5
        cv.put(_cov(_box_d(u + w / 2 - 0.05, v - y, 0.045, 0.009)), GOLD * 0.80)
    fr = _cov(_rbox_d(u - 0.04, v, w / 2 - 0.12, h / 2 - 0.075, 0.01)) * (1 - _cov(_rbox_d(u - 0.04, v, w / 2 - 0.138, h / 2 - 0.093, 0.01)))
    cv.put(fr, GOLD * 0.85)
    cv.put(_cov(_box_d(u - 0.04, v + h * 0.14, w * 0.20, 0.050)), PAPER * 0.85, 0.9)
    return cv.out()


def _stamp_over(A, Cp, cx, cy, half_m, painter, tile_m):
    """把 painter(dx, dy) 返回的 (alpha, 预乘 RGB) 以 over 叠进环面数组 A (n,n) / Cp (n,n,3)；(cx, cy) 周期单位。"""
    n = A.shape[0]
    px = tile_m / n
    Wd = min(int(math.ceil(half_m / px)) + 3, n // 2 - 1)
    ci, cj = int(round(cx * n - 0.5)), int(round(cy * n - 0.5))
    idx = np.arange(-Wd, Wd + 1)
    ii, jj = (ci + idx) % n, (cj + idx) % n
    dx = np.tile((idx * px)[None, :], (2 * Wd + 1, 1))
    dy = np.tile((idx * px)[:, None], (1, 2 * Wd + 1))
    a, cp = painter(dx, dy)
    sl = np.ix_(jj, ii)
    A0, C0 = A[sl], Cp[sl]
    A[sl] = a + A0 * (1.0 - a)
    Cp[sl] = cp + C0 * (1.0 - a)[..., None]


def _place_clusters(n, tile_m, rng, plan, edist):
    """冰下物件的簇心：环面上的最远点采样（簇间 ≥ 2.6 m），并且离冰板接缝 ≥ 0.9 m（物件在板子“里面”）。plan = [kind...]"""
    es = edist
    pts = []
    for kind in plan:
        best, best_d = None, -1.0
        for _ in range(260):
            cx, cy = rng.random(), rng.random()
            if es[int(cy * n) % n, int(cx * n) % n] < 0.95:
                continue
            d = min([math.hypot((cx - px_ + 0.5) % 1.0 - 0.5, (cy - py_ + 0.5) % 1.0 - 0.5) * tile_m for _, px_, py_ in pts] or [99.0])
            if d > best_d:
                best, best_d = (cx, cy), d
            if d > 4.4:
                break
        pts.append((kind, best[0], best[1]))
    return pts


def _under_ice(n, tile_m, rng, edist):
    """冰下的书 / 卷轴筒 / 圣物匣 / 散页：三个深度层，各自模糊并向冰色淡出。
    返回 (层列表 [(Ab (n,n), colb (n,n,3)) × 3], 簇数, 物件数)。"""
    A = [np.zeros((n, n)) for _ in range(3)]
    Cp = [np.zeros((n, n, 3)) for _ in range(3)]
    items = [0]

    def add(kind, cx, cy, ang, d, **k):
        d = int(np.clip(d, 0, 2))
        if kind == "page":
            w, h = k.get("w", rng.uniform(0.60, 0.76)), k.get("h", rng.uniform(0.82, 1.02))
            paper = PAPER * rng.uniform(0.80, 1.08)
            sk = rng.uniform(-0.12, 0.12)
            fn = lambda dx, dy: paint_page(*_rot(dx, dy, ang), w, h, paper, sk)
            half = math.hypot(w, h) / 2 + 0.06
        elif kind == "open":
            W, H = k.get("W", rng.uniform(0.66, 0.78)), k.get("H", rng.uniform(0.94, 1.08))
            lea = LEATHERS[int(rng.integers(len(LEATHERS)))]
            fn = lambda dx, dy: paint_open_book(*_rot(dx, dy, ang), W, H, lea)
            half = math.hypot(2 * W + 0.16, H + 0.16) / 2 + 0.06
        elif kind == "scroll":
            L, R = k.get("L", rng.uniform(1.35, 1.8)), rng.uniform(0.105, 0.135)
            fn = lambda dx, dy: paint_scroll(*_rot(dx, dy, ang), L, R)
            half = L / 2 + 0.46
        elif kind == "casket":
            W, H = k.get("W", rng.uniform(1.30, 1.65)), k.get("H", rng.uniform(0.88, 1.12))
            fn = lambda dx, dy: paint_casket(*_rot(dx, dy, ang), W, H)
            half = math.hypot(W, H) / 2 + 0.06
        else:
            w, h = rng.uniform(0.62, 0.74), rng.uniform(0.86, 1.02)
            lea = LEATHERS[int(rng.integers(len(LEATHERS)))]
            fn = lambda dx, dy: paint_book(*_rot(dx, dy, ang), w, h, lea)
            half = math.hypot(w, h) / 2 + 0.06
        _stamp_over(A[d], Cp[d], cx, cy, half, fn, tile_m)
        items[0] += 1

    plan = ["open"] * 4 + ["casket"] * 3 + ["scroll"] * 4 + ["books"] * 2 + ["pages"] * 2
    rng.shuffle(plan)
    clusters = _place_clusters(n, tile_m, rng, plan, edist)
    for kind, cx, cy in clusters:
        d = int(rng.choice([0, 0, 1, 1, 2]))
        ang = rng.uniform(0, math.pi)

        def around(r0, r1):
            a2 = rng.uniform(0, math.tau)
            rr = rng.uniform(r0, r1) / tile_m
            return cx + rr * math.cos(a2), cy + rr * math.sin(a2)

        if kind == "open":
            add("open", cx, cy, ang, d)
            for _ in range(int(rng.integers(2, 4))):
                x2, y2 = around(1.0, 1.6)
                add("page", x2, y2, rng.uniform(0, math.pi), d + int(rng.integers(0, 2)))
            if rng.random() < 0.6:
                x2, y2 = around(1.1, 1.7)
                add("book", x2, y2, rng.uniform(0, math.pi), d)
        elif kind == "casket":
            add("casket", cx, cy, ang, d)
            for _ in range(int(rng.integers(1, 3))):
                x2, y2 = around(1.1, 1.7)
                add("page", x2, y2, rng.uniform(0, math.pi), d + int(rng.integers(0, 2)))
            if rng.random() < 0.6:
                x2, y2 = around(1.2, 1.8)
                add("scroll", x2, y2, rng.uniform(0, math.pi), d)
        elif kind == "scroll":
            add("scroll", cx, cy, ang, d)
            if rng.random() < 0.5:
                add("scroll", cx + 0.38 / tile_m * math.cos(ang + 1.9), cy + 0.38 / tile_m * math.sin(ang + 1.9), ang + rng.uniform(0.35, 0.8), d)
            if rng.random() < 0.6:
                x2, y2 = around(0.9, 1.5)
                add("page", x2, y2, rng.uniform(0, math.pi), d)
        elif kind == "books":
            add("book", cx, cy, ang, d)
            add("book", cx + 0.30 / tile_m * math.cos(ang + 1.2), cy + 0.30 / tile_m * math.sin(ang + 1.2), ang + rng.uniform(0.3, 0.7), d)
            x2, y2 = around(0.9, 1.4)
            add("page", x2, y2, rng.uniform(0, math.pi), d)
        else:
            for _ in range(int(rng.integers(3, 5))):
                x2, y2 = around(0.0, 1.4)
                add("page", x2, y2, rng.uniform(0, math.pi), d + int(rng.integers(0, 2)))
    BLUR = [1.9, 3.0, 4.6]                    # 三个深度层的模糊（像素；1 px ≈ 2 cm）
    layers = []
    for d in range(3):
        Ab = np.clip(T.blur_periodic(A[d], BLUR[d]), 0.0, 1.0)
        Cb = np.clip(_blur3(Cp[d], BLUR[d]), 0.0, None)
        layers.append((Ab, Cb / np.maximum(Ab, 1e-4)[..., None]))
    return layers, len(clusters), items[0]


# =====================================================================
# 裂纹 / 气泡
# =====================================================================
def _seg_lines(dx, dy, segs, aa=0.004):
    """局部窗口里的折线集合 → 0..1 的线遮罩；segs = [(x0, y0, x1, y1, 半宽)...]（米）。"""
    out = np.zeros_like(dx)
    for x0, y0, x1, y1, hw in segs:
        ex, ey = x1 - x0, y1 - y0
        L2 = ex * ex + ey * ey + 1e-9
        t = np.clip(((dx - x0) * ex + (dy - y0) * ey) / L2, 0.0, 1.0)
        d = np.hypot(dx - (x0 + t * ex), dy - (y0 + t * ey))
        out = np.maximum(out, 1.0 - T.smoothstep(hw - aa, hw + aa, d))
    return out


def _star_cracks(rng, R):
    """冲击裂纹（蛛网）：放射状带折角的主裂 + 两圈不完整的环裂；返回线段列表（米，中心在原点）。"""
    segs = []
    k = int(rng.integers(6, 10))
    rays = []
    for i in range(k):
        th = math.tau * i / k + rng.uniform(-0.28, 0.28)
        Lr = R * rng.uniform(0.55, 1.0)
        pts = [(0.0, 0.0)]
        ang = th
        for j in range(1, 5):
            ang += rng.uniform(-0.16, 0.16)
            r = Lr * j / 4
            pts.append((r * math.cos(ang), r * math.sin(ang)))
        rays.append(pts)
        for j in range(4):
            hw = 0.0105 * (1 - j / 4) + 0.0035
            segs.append((*pts[j], *pts[j + 1], hw))
        if rng.random() < 0.55:                      # 分叉
            j = int(rng.integers(1, 3))
            bx, by = pts[j]
            ba = ang + rng.choice([-1, 1]) * rng.uniform(0.45, 0.8)
            segs.append((bx, by, bx + 0.45 * Lr * math.cos(ba), by + 0.45 * Lr * math.sin(ba), 0.0035))
    for j in (1, 2):
        for i in range(k):
            if rng.random() < 0.62:
                a, b = rays[i], rays[(i + 1) % k]
                if len(a) > j and len(b) > j:
                    segs.append((*a[j + 0], *b[j + 0], 0.0035))
    return segs


def _edge_cracks(n, tile_m, seed, wx, wy):
    """细一圈的沃罗诺伊（≈ 1.9 m 的格）边，随机留 1/3、整体弯曲：冻在冰里的裂纹网（断断续续，到处能接到接缝）。
    返回 (shallow, deep)：两组各自的 0..1 线遮罩（深的会被更大的模糊处理）。"""
    fs = tile_m / TILE_M
    vf = T.voronoi_tile(n, int(round(11 * fs)), 0.95, seed + 20)
    wx2 = wx + 0.10 * _gauss(n, seed + 31, 5 * fs, 18 * fs)
    wy2 = wy + 0.10 * _gauss(n, seed + 32, 5 * fs, 18 * fs)
    ef = _lookup(vf["e1"].astype(np.float64) * tile_m, wx2, wy2, tile_m)
    c1 = _lookup(vf["cid"], wx2, wy2, tile_m, nearest=True)
    c2 = _lookup(vf["nid"], wx2, wy2, tile_m, nearest=True)
    lo, hi = np.minimum(c1, c2), np.maximum(c1, c2)
    kept = T.rand01(lo, hi, seed + 22) < 0.36
    deep = T.rand01(lo, hi, seed + 23) < 0.55
    vary = 0.35 + 0.65 * T.smoothstep(0.30, 0.70, T.fbm_periodic(n, seed + 33, beta=1.6, kmin=6 * fs, kmax=40 * fs))
    hwid = 0.0042 + 0.0030 * T.fbm_periodic(n, seed + 34, beta=1.4, kmin=10 * fs, kmax=50 * fs)
    line = (1.0 - T.smoothstep(hwid * 0.5, hwid * 1.6, ef)) * kept * vary
    return line * (~deep), line * deep


def _bubbles(n, tile_m, rng, chains, clusters):
    """气泡串（沿一条弯线、大小渐变的一串珠）+ 气泡簇；返回 (亮环 0..1, 暗心 0..1)。"""
    L = Layer(n, tile_m)
    Dk = Layer(n, tile_m)

    def bubble(cx, cy, r):
        L.stamp(cx, cy, r + 0.04, lambda dx, dy: np.exp(-(((np.hypot(dx, dy) - r) / (0.010 + 0.06 * r)) ** 2)) * 0.85)
        Dk.stamp(cx, cy, r + 0.04, lambda dx, dy: (1.0 - T.smoothstep(r * 0.55, r * 0.95, np.hypot(dx, dy))) * 0.55)

    for _ in range(chains):
        cx, cy = rng.random(), rng.random()
        ang = rng.uniform(0, math.tau)
        r0, r1 = rng.uniform(0.022, 0.040), rng.uniform(0.05, 0.095)
        k = int(rng.integers(5, 11))
        x, y = cx * tile_m, cy * tile_m
        if rng.random() < 0.5:
            r0, r1 = r1, r0
        for j in range(k):
            r = r0 + (r1 - r0) * j / max(k - 1, 1)
            bubble(x / tile_m, y / tile_m, r)
            step = 2.1 * r + 0.03
            ang += rng.uniform(-0.28, 0.28)
            x += math.cos(ang) * step
            y += math.sin(ang) * step
    for _ in range(clusters):
        cx, cy = rng.random(), rng.random()
        for _ in range(int(rng.integers(5, 13))):
            rr = abs(rng.normal(0, 0.28))
            a2 = rng.uniform(0, math.tau)
            bubble(cx + rr * math.cos(a2) / tile_m, cy + rr * math.sin(a2) / tile_m, rng.uniform(0.018, 0.075))
    return L.a.astype(np.float64), Dk.a.astype(np.float64)


# =====================================================================
# 地面冰板
# =====================================================================
ICE_CORE = np.array([0.112, 0.145, 0.212])          # 板心：深而蓝黑的厚冰
ICE_MID = np.array([0.165, 0.210, 0.295])
ICE_SHALLOW = np.array([0.40, 0.49, 0.62])            # 靠缝处：薄而白（散射）
ICE_MILK = np.array([0.28, 0.35, 0.46])
FROST = np.array([0.60, 0.69, 0.82])
SEAM = np.array([0.84, 0.91, 1.00])
ENGRAVE = np.array([0.50, 0.58, 0.74])                 # 冰下星盘刻线的颜色：冷银
GRAIN_K, MICRO_K, CHIP_K = 0.020, 0.0004, 0.0022     # 颗粒（亮度）/ 霜面颗粒（法线）/ 缝边崩口（法线）的幅度：也是贴图 PNG 体积的主要来源
NORMAL_K = 1.2                                       # 材质的 normal_strength（贴图里的倾斜按它折算）


def _ice_surface(n, tile_m, cells, jitter, seed, rng, objects=True, glint=2, calm=1.0):
    """冰板的全部分层（地面 / 纹章共用）：返回 dict(rgb 线性, rough, height 米, tilt (ax, ay), 统计)。calm < 1 把接缝 / 裂纹 / 霜压淡（纹章要让位给星盘刻线）。
    rgb 是“相对冰色”的线性值（中值 ≈ 0.25）；height 不含板倾斜（倾斜直接写进法线，免得接缝处出现高度台阶）。"""
    px_m = tile_m / n
    fs = tile_m / TILE_M                       # 噪声频率按“每米”折算：纹章（30 m）和地面（20 m）的冰有同样的颗粒度

    def G(sd, kmin, kmax):
        return _gauss(n, seed + sd, kmin * fs, kmax * fs)

    def F(sd, beta, kmin, kmax):
        return T.fbm_periodic(n, seed + sd, beta=beta, kmin=kmin * fs, kmax=kmax * fs)

    wlx, wly = WARP_LOW * G(101, 2, 7), WARP_LOW * G(102, 2, 7)
    wx = wlx + 0.045 * G(103, 8, 26)
    wy = wly + 0.045 * G(104, 8, 26)
    vor = T.voronoi_tile(n, cells, jitter, seed)
    e_raw = _lookup(vor["e1"].astype(np.float64) * tile_m, wx, wy, tile_m)
    cid = _lookup(vor["cid"], wx, wy, tile_m, nearest=True)
    # 毛刺：缝线的锯齿
    e = np.abs(e_raw + 0.030 * G(105, 8, 26) + 0.009 * G(106, 40, 130))
    nw = T.smoothstep(0.30, 0.80, F(107, 1.8, 4, 34))
    hw = 0.011 + 0.060 * nw + 0.005 * G(108, 30, 110)           # 缝半宽（米）：宽窄变化
    hw = np.clip(hw, 0.008, 0.095)

    # —— 板的随机量 ——
    r_thick = T.rand01(cid, seed, 3)
    thick = 0.80 + 0.40 * r_thick
    cloud = F(1, 2.2, 2, 14)
    milky = T.smoothstep(0.55, 0.88, F(2, 2.2, 2, 9))
    grain = G(4, 70, 330)

    # —— 厚冰：板心深、靠缝浅（向下透）——
    shallow = 0.55 * np.exp(-e / 0.42) + 0.45 * np.exp(-e / 1.35)
    depthk = shallow * (1.12 - 0.35 * (thick - 0.8) / 0.4)
    rgb = ICE_CORE[None, None, :] * thick[..., None] + (ICE_SHALLOW - ICE_CORE)[None, None, :] * depthk[..., None]
    rgb = rgb * (0.88 + 0.24 * cloud)[..., None]
    rgb = _smooth_over(rgb, ICE_MILK, 0.40 * milky)
    wisp = T.smoothstep(0.35, 0.85, F(12, 2.4, 4, 34))
    rgb = rgb * (1.0 + 0.10 * wisp)[..., None]
    # 冰层的生长纹：每块板一个方向 / 间距的平行细带（沿板心坐标，环面上连续）
    X, Y = _grid(n)
    cxw = _lookup(vor["cx"].astype(np.float64), wx, wy, tile_m, nearest=True)
    cyw = _lookup(vor["cy"].astype(np.float64), wx, wy, tile_m, nearest=True)
    ddx = _wrap(X + wx / tile_m - cxw) * tile_m
    ddy = _wrap(Y + wy / tile_m - cyw) * tile_m
    th = T.rand01(cid, seed, 26) * math.pi
    lam = 0.55 + 0.9 * T.rand01(cid, seed, 27)
    sc = ddx * np.cos(th) + ddy * np.sin(th)
    band = np.cos(math.tau * sc / lam + math.tau * T.rand01(cid, seed, 28) + 2.2 * G(29, 3, 12))
    bmask = T.smoothstep(0.30, 0.75, F(30, 2.0, 2, 10))
    rgb = rgb * (1.0 + 0.085 * band * bmask * (0.4 + 0.6 * np.exp(-e / 1.4)))[..., None]

    # —— 冰下：深层裂纹 → 物件（深到浅）→ 浅层裂纹 / 气泡 ——
    crk_s, crk_d = _edge_cracks(n, tile_m, seed, wx, wy)
    cs = np.clip(T.blur_periodic(crk_s, 0.9) * 1.5, 0, 1)
    cd = np.clip(T.blur_periodic(crk_d, 2.0) * 1.6, 0, 1)
    rgb = _smooth_over(rgb, ICE_SHALLOW * 1.05, 0.34 * cd * calm)
    n_cl = n_it = 0
    if objects:
        layers, n_cl, n_it = _under_ice(n, tile_m, rng, e)
        VEIL = [0.20, 0.38, 0.55]              # 越深越被冰色“盖住”
        OPAC = [0.98, 0.90, 0.78]
        occ = sum(l[0] * w_ for l, w_ in zip(layers, (1.0, 0.8, 0.6)))
        rgb = rgb * (1.0 - 0.22 * np.clip(T.blur_periodic(occ, 7.0) * 2.2, 0, 1))[..., None]      # 物件四周冰里的暗晕（让轮廓分离出来）
        for d in (2, 1, 0):
            Ab, col = layers[d]
            col = col * (1 - VEIL[d]) + rgb * VEIL[d]
            rgb = _smooth_over(rgb, col, Ab * OPAC[d])
    rgb = _smooth_over(rgb, ICE_SHALLOW * 1.35, 0.46 * cs * calm)
    bl, bd = _bubbles(n, tile_m, rng, int(18 * (tile_m / TILE_M) ** 2), int(10 * (tile_m / TILE_M) ** 2))
    bl_b, bd_b = T.blur_periodic(bl, 0.8), T.blur_periodic(bd, 0.9)
    rgb = rgb * (1.0 - 0.34 * np.clip(bd_b, 0, 1))[..., None]
    rgb = _smooth_over(rgb, ICE_SHALLOW * 1.6, 0.42 * np.clip(bl_b, 0, 1))

    # —— 冲击裂纹（蛛网），表面的：亮线 + 沟 ——
    star = Layer(n, tile_m)
    for _ in range(int(4 * (tile_m / TILE_M) ** 2)):
        R = rng.uniform(1.0, 1.9)
        segs = _star_cracks(rng, R)
        cx, cy = rng.random(), rng.random()
        star.stamp(cx, cy, R + 0.2, lambda dx, dy, segs=segs: _seg_lines(dx, dy, segs))
    star_a = T.blur_periodic(star.a.astype(np.float64), 0.7)
    rgb = _smooth_over(rgb, ICE_SHALLOW * 1.5, 0.42 * calm * np.clip(star_a * 1.5, 0, 1))
    cs = np.clip(np.maximum(cs, star_a), 0, 1)

    # —— 霜：板缝两侧的一圈白蓝霜 + 表面霜斑 ——
    nh = T.smoothstep(0.25, 0.75, F(8, 1.6, 10, 90))
    halo_w = 0.07 + 0.16 * F(9, 1.6, 3, 20)
    halo = np.exp(-np.maximum(e - hw, 0.0) / halo_w) * (0.40 + 0.60 * nh)
    patch = T.smoothstep(0.52, 0.82, F(10, 2.0, 3, 26))
    frost = np.clip(0.80 * calm * halo + 0.40 * patch * (0.35 + 0.65 * np.exp(-e / 1.1)), 0, 1)
    rgb = _smooth_over(rgb, FROST * (0.82 + 0.20 * grain.clip(-1.5, 1.5) * 0.5)[..., None], 0.62 * frost)

    # —— 板缝：霜白的破裂边 + 宽处中心的暗缝 ——
    seam_core = 1.0 - T.smoothstep(hw * 0.65, hw * 1.20, e)
    sn = 0.80 + 0.20 * F(7, 1.0, 30, 200)
    rgb = _smooth_over(rgb, SEAM * sn[..., None], (0.55 + 0.37 * calm) * seam_core)
    crev = (1.0 - T.smoothstep(0.0, hw * 0.46, e)) * T.smoothstep(0.034, 0.062, hw)
    rgb = _smooth_over(rgb, ICE_CORE * 0.45, 0.80 * crev)
    # 表面细纹理：颗粒
    rgb = rgb * (1.0 + GRAIN_K * grain * (0.4 + frost))[..., None]
    rgb = np.clip(rgb, 0.0, 1.0)

    # —— 高度（米）：缝两侧的倒角 / 缝中心的缺口 / 崩口 / 表面裂纹的沟 / 缓缓的起伏 ——
    ng = T.smoothstep(0.20, 0.80, F(13, 1.8, 4, 30))
    nc = F(14, 1.8, 4, 30)
    groove = 0.010 + 0.020 * ng
    cham = 0.040 + 0.085 * nc
    h = -groove * (1.0 - T.smoothstep(0.0, cham, e)) - 0.007 * seam_core - 0.004 * crev
    h += CHIP_K * G(15, 50, 200) * np.exp(-e / 0.16)                  # 缝边崩口
    h -= 0.0036 * np.clip(T.blur_periodic(cs, 0.6) * 1.4, 0, 1)                        # 表面裂纹的细沟
    h += 0.003 * G(16, 3, 18)                                           # 冰面缓起伏
    h += MICRO_K * G(17, 90, 360) * (0.3 + frost)                       # 霜处的颗粒

    # —— 板倾斜（法线空间；ax 正 = 法线朝东，ay 正 = 法线朝北）——
    # 每块板略有倾斜并带一点“弓”（倾斜随离板心的距离线性变化）：约 glint 的板，板心附近刚好把轮廓光（NE 偏北）反射向镜头 → 一片冷色高光；
    # 其余的板倾斜随机且小，偶尔扫过。倾斜写进法线（不进高度，免得接缝处出现高度台阶）。
    X, Y = _grid(n)
    cxw = _lookup(vor["cx"].astype(np.float64), wx, wy, tile_m, nearest=True)
    cyw = _lookup(vor["cy"].astype(np.float64), wx, wy, tile_m, nearest=True)
    ddx = _wrap(X + wx / tile_m - cxw) * tile_m
    ddy = _wrap(Y + wy / tile_m - cyw) * tile_m
    ra, rb = T.rand01(cid, seed, 21), T.rand01(cid, seed, 22)
    ncell = cells * cells
    order = np.argsort(T.rand01(np.arange(ncell), seed, 23))[:glint]       # 每个周期里只有 glint 块板带高光（重复时不会有一堆一样的亮斑）
    is_g = np.isin(cid, order)
    off = np.where(cid == order[-1], 1.0, 0.0) if glint > 1 else 0.0           # 最后一块偏离一点，亮度低一些
    ax0 = np.where(is_g, 0.285 - 0.075 * off + 0.02 * (ra - 0.5) * 2, 0.055 * (ra - 0.5) * 2)
    ay0 = np.where(is_g, 0.075 + 0.05 * off + 0.02 * (rb - 0.5) * 2, 0.055 * (rb - 0.5) * 2)
    ax = ax0 + (T.rand01(cid, seed, 24) * 2 - 1) * np.where(is_g, 0.060, 0.022) * ddx
    ay = ay0 + (T.rand01(cid, seed, 25) * 2 - 1) * np.where(is_g, 0.060, 0.022) * ddy
    ax, ay = T.blur_periodic(ax, 1.6), T.blur_periodic(ay, 1.6)

    # —— 粗糙度：清冰低、霜 / 缝高 ——
    glint_k = T.blur_periodic(is_g.astype(np.float64), 2.0)
    rough = 0.235 + 0.07 * glint_k + 0.07 * cloud + 0.28 * frost + 0.36 * seam_core + 0.14 * np.clip(cs, 0, 1) + 0.10 * milky      # 带高光的板稍粗：高光是一片柔和的冷光，不是一面镜子
    return dict(rgb=rgb, rough=np.clip(rough, 0.14, 0.92), h=h, ax=ax, ay=ay, px_m=px_m, clusters=n_cl, items=n_it, e=e, frost=frost)


def _normal_from(h, ax, ay, px_m, k_h=1.0):
    """高度（米）+ 板倾斜 → 切线空间法线（glTF 约定，与 T.normal_from_height 同一方向定义）；贴图里的倾斜按材质 normal_strength 折算。"""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) / (2.0 * px_m)
    drow = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) / (2.0 * px_m)
    nx = -dx * k_h + ax / NORMAL_K
    ny = drow * k_h + ay / NORMAL_K
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    out = np.stack([nx / ln, ny / ln, nz / ln], axis=-1) * 0.5 + 0.5
    return (np.clip(out, 0, 1) * 255.0 + 0.5).astype(np.uint8)


def make_floor(n=1024, seed=FLOOR_SEED, cells=FLOOR_CELLS, mr_size=512):
    """返回 dict：base / normal（uint8 RGB，n×n）、mr（uint8 RGB，mr_size²：G 粗糙度 B 金属度）、stats。"""
    rng = np.random.default_rng(seed)
    ice = _ice_surface(n, TILE_M, cells, FLOOR_JITTER, seed, rng)
    base_lin = ice["rgb"]
    normal = _normal_from(ice["h"], ice["ax"], ice["ay"], ice["px_m"])
    rough = ice["rough"]
    mr = np.stack([np.zeros_like(rough), rough, np.zeros_like(rough)], axis=-1)
    k = n // mr_size
    mr = mr.reshape(mr_size, k, mr_size, k, 3).mean(axis=(1, 3))
    ref = float((0.2126 * base_lin[..., 0] + 0.7152 * base_lin[..., 1] + 0.0722 * base_lin[..., 2]).mean())
    return dict(base=T.to_u8(T.lin_to_srgb(base_lin)), normal=normal, mr=T.to_u8(mr), stats=dict(items=ice["items"], clusters=ice["clusters"], ref=ref))



# =====================================================================
# 冰下星盘纹章（30 m 圆；贴图覆盖 [-15,15]² 米，1024²）
# =====================================================================
def make_emblem(n=1024, seed=71):
    R = EMBLEM_R
    px_m = 2 * R / n
    xs = (np.arange(n) + 0.5) / n * 2 * R - R
    X, Z = np.meshgrid(xs, xs)                 # X 向东，Z 向南（行向下）
    r = np.hypot(X, Z)
    th = np.arctan2(Z, X)
    aa = 1.5 * px_m
    rng = np.random.default_rng(seed)

    def inside(d):
        return T.smoothstep(-aa, aa, d)

    def line(d, w):
        return 1.0 - T.smoothstep(w - aa, w + aa, np.abs(d))

    def ring(r0, r1):
        return inside(r - r0) * inside(r1 - r)

    dark = np.zeros((n, n))                    # 剪影（深色）
    lite = np.zeros((n, n))                    # 细节（浅色边）
    gem = np.zeros((n, n))                     # 自发光点

    def put(mask, w=1.0, light=0.0):
        nonlocal dark, lite
        dark = np.maximum(dark, mask * w)
        if light:
            lite = np.maximum(lite, mask * light)

    # 1) 外圈双线 + 最外侧“接缝圈”
    put(line(r - 14.55, 0.07))
    put(line(r - 14.30, 0.035))
    put(line(r - 13.62, 0.05))
    # 2) 刻度环：每 2.5° 一格，每 15° 一格长刻度，每 30° 一个标记块
    tt = th / math.tau * 144.0
    minor = np.abs(((tt + 0.5) % 1.0) - 0.5) * (math.tau * r / 144.0) < 0.030
    major = np.abs(((th / math.tau * 24.0 + 0.5) % 1.0) - 0.5) * (math.tau * r / 24.0) < 0.040
    put(minor * ring(13.78, 14.18) + major * ring(13.66, 14.28), 0.9)
    block = (np.abs(((th / math.tau * 12.0 + 0.5) % 1.0) - 0.5) * (math.tau * r / 12.0) < 0.22) * ring(14.36, 14.50)
    put(block, 0.85)
    for k in range(24):                        # 发光节点：外圈 24 个小圆点
        a = (k + 0.5) * math.tau / 24
        gem = np.maximum(gem, inside(0.085 - np.hypot(X - 14.42 * math.cos(a), Z - 14.42 * math.sin(a))))
    # 3) 黄道带：12 格 + 每格一个符号
    put(line(r - 11.2, 0.06) + line(r - 13.4, 0.06), 1.0)
    div = np.abs(((th / math.tau * 12.0 + 0.5) % 1.0) - 0.5) * r * math.tau / 12.0
    put(line(div, 0.03) * ring(11.2, 13.4), 0.8)
    glyph_r = 12.3

    def glyph(kind, cx, cz, size):
        dx, dz = X - cx, Z - cz
        d = np.hypot(dx, dz)
        s = size
        if kind == 0:                          # 四角星（星形线）
            a23 = (0.5 * s) ** (2 / 3)
            val = np.abs(dx) ** (2 / 3) + np.abs(dz) ** (2 / 3)
            return 1.0 - T.smoothstep(a23 * 0.96, a23 * 1.04, val)
        if kind == 1:                          # 新月
            return inside(0.46 * s - d) * (1 - inside(0.40 * s - np.hypot(dx - 0.22 * s, dz)))
        if kind == 2:                          # 圆 + 点
            return np.maximum(line(d - 0.40 * s, 0.07 * s), inside(0.10 * s - d))
        if kind == 3:                          # 三角（轮廓）
            dd = np.maximum(dz - 0.28 * s, 0.866 * np.abs(dx) - 0.5 * dz - 0.20 * s)
            return line(dd, 0.06 * s)
        if kind == 4:                          # 菱形（轮廓）
            return line((np.abs(dx) + np.abs(dz)) - 0.46 * s, 0.07 * s)
        if kind == 5:                          # 十字
            return np.maximum(line(dx, 0.07 * s) * inside(0.44 * s - np.abs(dz)), line(dz, 0.07 * s) * inside(0.44 * s - np.abs(dx)))
        if kind == 6:                          # 三叶
            m = np.zeros_like(d)
            for j in range(3):
                a = j * math.tau / 3 + 0.5
                m = np.maximum(m, line(np.hypot(dx - 0.22 * s * math.cos(a), dz - 0.22 * s * math.sin(a)) - 0.17 * s, 0.05 * s))
            return m
        return line(np.maximum(np.abs(dx) * 0.7, np.abs(dz)) - 0.40 * s, 0.07 * s)          # 方框
    for k in range(12):
        a = (k + 0.5) * math.tau / 12
        gx_, gz_ = glyph_r * math.cos(a), glyph_r * math.sin(a)
        put(glyph(k % 8, gx_, gz_, 1.15) * ring(11.3, 13.3), 0.95, light=0.5)
    # 4) 铭文环：96 格，每格一段随机长度的短线（像一圈文字）
    cellid = np.floor((th + math.pi) / math.tau * 96.0).astype(int) % 96
    frac = ((th + math.pi) / math.tau * 96.0) % 1.0
    ln = 0.35 + 0.55 * T.rand01(cellid, seed, 2)
    off = 0.5 * (1 - ln)
    dash = ((frac > off) & (frac < off + ln)) * ring(10.15, 10.45)
    dash2 = ((frac > 0.5 * (1 - (0.3 + 0.5 * T.rand01(cellid, seed, 4)))) & (frac < 1 - 0.5 * (1 - (0.3 + 0.5 * T.rand01(cellid, seed, 4))))) * ring(9.75, 10.00)
    put(dash * 0.9 + dash2 * 0.7, 1.0)
    put(line(r - 10.62, 0.04) + line(r - 9.58, 0.04), 1.0)
    # 5) 网板（rete）：偏心圆 + 外尖刺（星指针）
    put(line(np.hypot(X - 0.0, Z + 1.7) - 7.3, 0.08), 1.0, light=0.3)
    put(line(np.hypot(X + 0.5, Z - 1.2) - 5.4, 0.05), 0.9)
    put(line(r - 8.6, 0.05), 0.85)
    for k in range(8):                         # 外尖刺
        a = k * math.tau / 8 + math.pi / 8
        da = np.angle(np.exp(1j * (th - a)))
        taper = np.clip(1.0 - (r - 8.7) / 0.9, 0.0, 1.0)
        spike = inside(0.12 * taper - np.abs(da) * r) * ring(8.7, 9.6)
        put(spike, 0.9, light=0.4)
    # 6) 罗盘玫瑰：16 角星（8 长 / 8 中），外接圆
    def star(pts, length, half_w, rot=0.0):
        m = np.zeros((n, n))
        for k in range(pts):
            a = rot + k * math.tau / pts
            da = np.angle(np.exp(1j * (th - a)))
            lim = length * (1.0 - np.abs(da) / half_w)
            m = np.maximum(m, inside(lim - r) * (np.abs(da) < half_w))
        return m
    s_long = star(8, 8.0, 0.20)
    s_mid = star(8, 5.4, 0.26, math.pi / 8)
    s_small = star(16, 3.2, 0.20, math.pi / 16)
    put(s_long, 0.78, light=0.45)
    put(s_mid, 0.70, light=0.35)
    put(s_small, 0.60)
    # 星的“明暗对半”：每个尖角一侧略深，一侧略浅（用角度符号做出立体感）
    side = (np.sin(th * 8 + 0.0) > 0).astype(float)
    dark = dark * (1.0 - 0.18 * side * np.maximum(s_long, s_mid))
    # 7) 中心：圆环 + 宝石
    put(line(r - 1.55, 0.07) + line(r - 0.95, 0.04), 1.0, light=0.4)
    put(inside(0.38 - r), 1.0, light=0.0)
    gem = np.maximum(gem, inside(0.20 - r))
    # 8) 测高尺（alidade）：穿过圆心的长条，端部有环
    ang = math.radians(28.0)
    u = X * math.cos(ang) + Z * math.sin(ang)
    v = -X * math.sin(ang) + Z * math.cos(ang)
    bar = inside(0.17 - np.abs(v)) * inside(9.4 - np.abs(u)) * (np.abs(u) > 1.6)
    put(bar, 0.8, light=0.45)
    for s_ in (-1, 1):
        put(line(np.hypot(u - s_ * 9.8, v) - 0.42, 0.06), 0.95)
        put(inside(0.14 - np.hypot(u - s_ * 9.8, v)), 1.0)
    # 9) 纬度弧：不完整的同心弧
    for rr, a0, a1 in ((3.0, 0.4, 2.6), (4.2, 3.4, 5.9), (6.0, -0.5, 1.1), (6.4, 2.2, 4.4)):
        da = np.angle(np.exp(1j * (th - (a0 + a1) / 2)))
        put(line(r - rr, 0.04) * (np.abs(da) < (a1 - a0) / 2), 0.85)
    # 10) 星点：散在网板里的小圆点，一部分发光
    for k in range(34):
        a, rr = rng.uniform(0, math.tau), rng.uniform(2.0, 8.3)
        sx, sz = rr * math.cos(a), rr * math.sin(a)
        if np.hypot(sx, sz) < 1.8:
            continue
        dd = np.hypot(X - sx, Z - sz)
        put(inside(0.13 - dd), 0.9, light=0.6)
        if k % 5 == 0:
            gem = np.maximum(gem, inside(0.085 - dd))

    # —— 冰：与地面同一套分层（厚冰深浅 / 霜边的破裂接缝 / 冻裂纹 / 气泡 / 板倾斜），只是没有物件（星盘本身就是冰下的封存物）——
    ice = _ice_surface(n, 2 * R, 6, 0.8, seed, np.random.default_rng(seed + 5), objects=False, glint=0, calm=0.55)
    base_rgb = ice["rgb"]
    frost = ice["frost"]

    # —— 刻线（冰下封着的星盘：冷银色的细刻线，两层模糊；板心很暗，所以刻线取“比冰亮”，靠近缝的亮冰处则略压暗）——
    d_soft = np.clip(0.62 * T.blur_periodic(dark, 1.3) + 0.38 * T.blur_periodic(dark, 3.6), 0, 1)
    l_soft = np.clip(0.6 * T.blur_periodic(lite, 1.3) + 0.4 * T.blur_periodic(lite, 3.2), 0, 1)
    k_eng = 0.80 * d_soft * (1.0 - 0.55 * np.clip(frost, 0, 1))
    rgb = _smooth_over(base_rgb, ENGRAVE, k_eng)
    rgb = rgb + (ICE_SHALLOW * 0.55)[None, None, :] * (0.45 * l_soft)[..., None]

    # —— 圆盘外缘：一圈霜白的接缝（与地面板缝同质）——
    rim_d = np.abs(r - (R - 0.06))
    rim = 1.0 - T.smoothstep(0.012, 0.045, rim_d)
    rgb = _smooth_over(rgb, SEAM * 0.9, 0.85 * rim)
    rim_halo = np.exp(-np.maximum(rim_d - 0.04, 0.0) / 0.12) * (r < R - 0.06)
    rgb = _smooth_over(rgb, FROST, 0.30 * rim_halo)
    outside = r > R - 0.02
    rgb[outside] = ice["rgb"][outside] * 0.9
    rgb = np.clip(rgb, 0.0, 1.0)

    # —— 法线 / 粗糙度：冰面（含倾斜与接缝倒角）+ 外缘的倒角；冰下刻线只带一点点折射的起伏 ——
    h = ice["h"] - 0.012 * rim * (~outside) + 0.0008 * T.blur_periodic(dark, 3.0)
    normal = _normal_from(h, ice["ax"], ice["ay"], ice["px_m"])
    rough = np.clip(ice["rough"] + 0.30 * rim, 0.14, 0.92)
    emissive = np.clip(gem, 0, 1)[..., None] * _lin("#a9c4ea")[None, None, :]
    return dict(base=T.to_u8(T.lin_to_srgb(rgb)), normal=normal, rough=rough, emissive=T.to_u8(T.lin_to_srgb(emissive)),
                stats=dict(ref=float((0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).mean()),
                           gem=float((gem > 0.2).mean())))


# =====================================================================
# 冻石（4 m 周期、512²，可平铺）：暗钢蓝灰石板 + 霜斑 + 发丝裂纹
# =====================================================================
def make_stone(n=512, seed=21):
    px_m = STONE_M / n
    m1 = T.fbm_periodic(n, seed, beta=2.4, kmin=1, kmax=8)
    m2 = T.fbm_periodic(n, seed + 1, beta=1.0, kmin=14, kmax=110)
    m3 = T.fbm_periodic(n, seed + 3, beta=2.0, kmin=3, kmax=20)
    rid = T.fbm_periodic(n, seed + 5, beta=2.2, kmin=2, kmax=14)
    rmask = T.smoothstep(0.54, 0.70, T.fbm_periodic(n, seed + 7, beta=3.0, kmin=1, kmax=5))
    crack = (1.0 - T.smoothstep(0.003, 0.016, np.abs(rid - 0.5))) * rmask
    frost = T.smoothstep(0.60, 0.80, T.fbm_periodic(n, seed + 11, beta=2.0, kmin=3, kmax=26))
    speck = T.smoothstep(0.62, 0.9, T.fbm_periodic(n, seed + 12, beta=0.5, kmin=60, kmax=250))
    lum = 0.32 + 0.07 * (m1 - 0.5) * 2 + 0.05 * (m2 - 0.5) * 2 + 0.035 * (m3 - 0.5) * 2
    lum = lum * (1 - 0.40 * crack)
    lum = lum * (1.0 + 0.30 * frost) + 0.10 * speck * frost
    lum = lum + 0.25 * crack * frost                    # 裂缝里结霜
    tintc = np.array([0.92, 0.99, 1.07])
    base = np.clip(lum[..., None] * tintc[None, None, :], 0, 1)
    h = 0.008 * (m1 - 0.5) + 0.004 * (m2 - 0.5) + 0.003 * (m3 - 0.5) - 0.006 * crack + 0.0014 * speck
    normal = T.normal_from_height(h, px_m, 1.1)
    return dict(base=T.to_u8(base), normal=normal)


# =====================================================================
# 书架墙（4 m × 4 m 周期、512²，可平铺）：8 层书架，每层一排书脊 + 层板；霜斑覆盖
# =====================================================================
BOOK_COLORS = [("#3a261d", 3), ("#4a2c26", 2), ("#2c3345", 3), ("#37402f", 2), ("#6a5a42", 2), ("#1c1b21", 3), ("#4a3a2a", 3), ("#2f3a3c", 1)]
GILT = "#8a7648"


def make_bookwall(n=512, seed=51):
    rng = np.random.default_rng(seed)
    px_m = SHELF_M / n
    rows = 8
    row_px = n // rows
    cols = [c for c, w in BOOK_COLORS for _ in range(w)]
    img = np.zeros((n, n, 3))
    hgt = np.zeros((n, n))
    bg = _lin("#0c0e13")
    img[:] = bg
    hgt[:] = -0.040
    wood = _lin("#2a211c")
    for ri in range(rows):
        y_bot = (ri + 1) * row_px                      # 行底（图像下方）
        board = 5
        img[y_bot - board:y_bot] = wood * (0.9 + 0.2 * rng.random())
        img[y_bot - board] = wood * 1.6               # 层板前沿高光
        hgt[y_bot - board:y_bot] = 0.020
        x = 0
        shelf_h = row_px - board
        while x < n:
            if rng.random() < 0.06:                    # 空位
                x += int(rng.integers(3, 9))
                continue
            w = int(rng.integers(4, 12))
            if x + w > n:
                w = n - x
            hb = int(shelf_h * rng.uniform(0.62, 0.97))
            col = _lin(cols[int(rng.integers(len(cols)))]) * rng.uniform(0.75, 1.25)
            lean = rng.random() < 0.05
            y0 = y_bot - board - hb
            for dx in range(w):
                sh = int(dx * 0.25 * hb / max(w, 1) * 0.5) if lean else 0
                ya, yb = y0 + sh, y_bot - board
                if ya >= yb:
                    continue
                shade = 1.0 - 0.35 * (dx == 0) - 0.20 * (dx == w - 1) + 0.08 * (dx == w // 2)
                img[ya:yb, (x + dx) % n] = col * shade
                hgt[ya:yb, (x + dx) % n] = 0.012 + 0.010 * (dx > 0) * (dx < w - 1) * rng.random()
            # 书脊装饰：上下烫金带、标签、横脊
            if rng.random() < 0.45 and hb > 18 and not lean:
                for yy in (y0 + 3, y0 + 5, y_bot - board - 5, y_bot - board - 7):
                    if rng.random() < 0.7:
                        img[yy, x + 1:x + w - 1] = _lin(GILT) * rng.uniform(0.7, 1.1)
            if rng.random() < 0.25 and hb > 20 and w >= 6 and not lean:
                ly = y0 + int(hb * rng.uniform(0.3, 0.6))
                img[ly:ly + 6, x + 1:x + w - 1] = _lin("#7a6e54") * rng.uniform(0.5, 0.9)
            x += w + (1 if rng.random() < 0.5 else 0)
        # 本层顶部暗影
        img[ri * row_px:ri * row_px + row_px // 3] *= np.linspace(0.55, 1.0, row_px // 3)[:, None, None]
    # 冰壳 / 霜：局部覆盖一层冷灰蓝，并提亮
    frost = T.smoothstep(0.55, 0.78, T.fbm_periodic(n, seed + 2, beta=2.0, kmin=2, kmax=18))
    frost2 = T.smoothstep(0.50, 0.80, T.fbm_periodic(n, seed + 3, beta=1.2, kmin=8, kmax=60))
    fcol = _lin("#6a7a8e")
    k = np.clip(0.55 * frost + 0.25 * frost2 * frost, 0, 0.75)
    img = img * (1 - k[..., None]) + fcol[None, None, :] * k[..., None] * 0.9
    # 灰尘 / 明暗
    img = img * (0.86 + 0.28 * T.fbm_periodic(n, seed + 4, beta=1.6, kmin=3, kmax=40))[..., None]
    h = T.blur_periodic(hgt, 0.7) + 0.0016 * (T.fbm_periodic(n, seed + 5, beta=0.8, kmin=60, kmax=220) - 0.5) + 0.004 * k
    normal = T.normal_from_height(h, px_m, 1.0)
    return dict(base=T.to_u8(T.lin_to_srgb(np.clip(img, 0, 1))), normal=normal)


# =====================================================================
# 冰壳法线（3 m 周期、512²，可平铺）：晶面 + 裂纹 + 细刮痕（只有法线；基础色由材质色 + 顶点色给）
# =====================================================================
def make_ice_normal(n=512, seed=91):
    px_m = ICE_M / n
    vor = T.voronoi_tile(n, 9, 0.9, seed)
    cid = vor["cid"]
    xs = (np.arange(n) + 0.5) / n
    X, Y = np.meshgrid(xs, xs)
    ddx, ddy = _wrap(X - vor["cx"]), _wrap(Y - vor["cy"])
    a = (T.rand01(cid, seed, 1) - 0.5) * 0.9
    b = (T.rand01(cid, seed, 2) - 0.5) * 0.9
    facet = (a * ddx + b * ddy) * ICE_M * 0.06
    e1m = vor["e1"].astype(np.float64) * ICE_M
    bevel = T.smoothstep(0.0, 0.02, e1m)
    fine = T.voronoi_tile(n, 30, 1.0, seed + 3)
    crack = (fine["e1"].astype(np.float64) * ICE_M < 0.006) * T.smoothstep(0.5, 0.7, T.fbm_periodic(n, seed + 4, beta=2.4, kmin=1, kmax=5))
    scr = T.fbm_periodic(n, seed + 5, beta=0.7, kmin=40, kmax=200) - 0.5
    h = T.blur_periodic(facet, 0.8) - 0.004 * (1 - bevel) - 0.004 * T.blur_periodic(crack, 0.8) + 0.0010 * scr
    return dict(normal=T.normal_from_height(h, px_m, 1.1))


if __name__ == "__main__":
    import sys
    import time
    from pathlib import Path
    out = Path(sys.argv[1])
    which = sys.argv[2] if len(sys.argv) > 2 else "floor"
    t = time.time()
    r = dict(floor=make_floor, emblem=make_emblem, stone=make_stone, books=make_bookwall, ice=make_ice_normal)[which]()
    print(which, time.time() - t, r.get("stats"))
    for k, v in r.items():
        if k != "stats":
            print(k, T.write_png(out / f"{which}_{k}.png", v))
