"""场地贴图工具（纯 numpy，不依赖 Blender）：可平铺噪声 / 沃罗诺伊 / 法线 / PNG 写出。

所有“可平铺”函数都在 n×n 的环面上计算（首尾相接），贴图重复时没有接缝。
数组约定：第 0 行 = 图像最上方（与 PNG 一致）；贴图坐标里“上” = 北（−Z），“右” = 东（+X）。
"""

import struct
import zlib

import numpy as np


# ===== 基础函数 =====
def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def hash_u32(a, b=0, c=0):
    """整数哈希 → uint32（向量化）。"""
    x = (np.asarray(a, dtype=np.uint64) * np.uint64(0x9E3779B1) + np.asarray(b, dtype=np.uint64) * np.uint64(0x85EBCA77)
         + np.asarray(c, dtype=np.uint64) * np.uint64(0xC2B2AE3D) + np.uint64(0x27D4EB2F)) & np.uint64(0xFFFFFFFF)
    x ^= x >> np.uint64(15)
    x = (x * np.uint64(0x2C1B3C6D)) & np.uint64(0xFFFFFFFF)
    x ^= x >> np.uint64(12)
    x = (x * np.uint64(0x297A2D39)) & np.uint64(0xFFFFFFFF)
    x ^= x >> np.uint64(15)
    return x.astype(np.uint32)


def rand01(a, b=0, c=0):
    return hash_u32(a, b, c).astype(np.float64) / 4294967296.0


# ===== 可平铺噪声 =====
def fbm_periodic(n, seed, beta=2.0, kmin=1.0, kmax=None):
    """频域滤波的可平铺噪声：功率谱 ∝ k^-beta，kmin / kmax 为每个贴图周期内的频率范围；返回 0..1，均值 0.5。"""
    rng = np.random.default_rng(seed)
    spec = np.fft.fft2(rng.standard_normal((n, n)))
    f = np.fft.fftfreq(n) * n
    k = np.hypot(f[:, None], f[None, :])
    k[0, 0] = 1.0
    amp = k ** (-beta / 2.0)
    amp[k < kmin] = 0.0
    if kmax is not None:
        amp[k > kmax] = 0.0
    amp[0, 0] = 0.0
    out = np.fft.ifft2(spec * amp).real
    out = out / (out.std() * 4.0 + 1e-9) + 0.5
    return np.clip(out, 0.0, 1.0)


def blur_periodic(a, radius_px):
    """环面上的高斯模糊（频域）。"""
    n = a.shape[0]
    f = np.fft.fftfreq(n)
    k2 = f[:, None] ** 2 + f[None, :] ** 2
    g = np.exp(-2.0 * (np.pi * radius_px) ** 2 * k2)
    return np.fft.ifft2(np.fft.fft2(a) * g).real


def sample_periodic(a, x, y):
    """在 [0,1) 的环面坐标上双线性采样 a（形状 n×n）；x 向右（列），y 向下（行）。"""
    n = a.shape[0]
    fx, fy = (np.asarray(x) % 1.0) * n - 0.5, (np.asarray(y) % 1.0) * n - 0.5
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    x0, y0, x1, y1 = x0 % n, y0 % n, (x0 + 1) % n, (y0 + 1) % n
    return (a[y0, x0] * (1 - tx) * (1 - ty) + a[y0, x1] * tx * (1 - ty) + a[y1, x0] * (1 - tx) * ty + a[y1, x1] * tx * ty)


# ===== 沃罗诺伊（环面）=====
def voronoi_tile(n, cells, jitter, seed):
    """n×n 像素、每边 cells 个种子的可平铺沃罗诺伊。返回 dict：
    cid   像素所属单元编号（0..cells²-1）；
    e1    到最近单元边界的距离（贴图周期 = 1 的单位）；e2 第二近的另一条边；
    nid   最近边另一侧的单元编号；cx, cy 种子位置（单元中心，周期单位，已折回 [0,1)）。"""
    rng = np.random.default_rng(seed)
    jx, jy = rng.random((cells, cells)), rng.random((cells, cells))

    def seed_pos(i, j):
        ii, jj = i % cells, j % cells
        return (i + 0.5 + jitter * (jx[ii, jj] - 0.5)) / cells, (j + 0.5 + jitter * (jy[ii, jj] - 0.5)) / cells

    xs = ((np.arange(n) + 0.5) / n).astype(np.float32)
    X, Y = np.meshgrid(xs, xs)
    ci, cj = np.floor(X * cells).astype(np.int32), np.floor(Y * cells).astype(np.int32)
    best = np.full((n, n), 9.0, np.float32)
    bi, bj = ci.copy(), cj.copy()
    bx, by = X.copy(), Y.copy()
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            sx, sy = seed_pos(ci + di, cj + dj)
            d = (X - sx) ** 2 + (Y - sy) ** 2
            m = d < best
            best = np.where(m, d, best)
            bi = np.where(m, ci + di, bi)
            bj = np.where(m, cj + dj, bj)
            bx = np.where(m, sx, bx)
            by = np.where(m, sy, by)
    e1 = np.full((n, n), 9.0, np.float32)
    e2 = np.full((n, n), 9.0, np.float32)
    n1 = np.zeros((n, n), np.int32)
    for di in (-2, -1, 0, 1, 2):
        for dj in (-2, -1, 0, 1, 2):
            ii, jj = ci + di, cj + dj
            sx, sy = seed_pos(ii, jj)
            same = (ii == bi) & (jj == bj)
            dab = np.sqrt((sx - bx) ** 2 + (sy - by) ** 2) + 1e-9
            d = ((X - sx) ** 2 + (Y - sy) ** 2 - best) / (2.0 * dab)
            d = np.where(same, 9.0, d)
            m1 = d < e1
            m2 = (~m1) & (d < e2)
            e2 = np.where(m1, e1, np.where(m2, d, e2))
            n1 = np.where(m1, (ii % cells) * cells + (jj % cells), n1)
            e1 = np.where(m1, d, e1)
    cid = ((bi % cells) * cells + (bj % cells)).astype(np.int32)
    return dict(cid=cid, e1=e1, e2=e2, nid=n1, cx=bx % 1.0, cy=by % 1.0, cells=cells, cell_dist=np.sqrt(best))


# ===== 法线 =====
def normal_from_height(h_m, px_m, strength=1.0):
    """高度图（米）→ glTF / OpenGL 约定的切线空间法线（uint8 RGB）。px_m = 每像素的米数。
    图像“右” = +X，图像“上” = 北；绿色通道指向图像上方。"""
    dx = (np.roll(h_m, -1, axis=1) - np.roll(h_m, 1, axis=1)) / (2.0 * px_m)
    drow = (np.roll(h_m, -1, axis=0) - np.roll(h_m, 1, axis=0)) / (2.0 * px_m)
    nx = -dx * strength
    ny = drow * strength              # 行增大 = 图像向下；向上的斜率 = -drow，法线朝斜坡反方向 → +drow
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    out = np.stack([nx / ln, ny / ln, nz / ln], axis=-1) * 0.5 + 0.5
    return (np.clip(out, 0, 1) * 255.0 + 0.5).astype(np.uint8)


def to_u8(rgb):
    return (np.clip(rgb, 0, 1) * 255.0 + 0.5).astype(np.uint8)


# ===== PNG 写出（自适应行滤波 + zlib 9，比 Blender 直接存的更小）=====
def _paeth(a, b, c):
    p = a.astype(np.int16) + b - c
    pa, pb, pc = np.abs(p - a), np.abs(p - b), np.abs(p - c)
    return np.where((pa <= pb) & (pa <= pc), a, np.where(pb <= pc, b, c)).astype(np.uint8)


def png_bytes(arr):
    arr = np.ascontiguousarray(arr, dtype=np.uint8)
    h, w = arr.shape[:2]
    c = 1 if arr.ndim == 2 else arr.shape[2]
    ctype = {1: 0, 2: 4, 3: 2, 4: 6}[c]
    raw = arr.reshape(h, w * c)
    left = np.zeros_like(raw)
    left[:, c:] = raw[:, :-c]
    up = np.zeros_like(raw)
    up[1:] = raw[:-1]
    ul = np.zeros_like(raw)
    ul[1:, c:] = raw[:-1, :-c]
    cands = [
        raw,
        (raw - left).astype(np.uint8),
        (raw - up).astype(np.uint8),
        (raw - ((left.astype(np.uint16) + up) >> 1).astype(np.uint8)).astype(np.uint8),
        (raw - _paeth(left, up, ul)).astype(np.uint8),
    ]
    cost = np.stack([np.minimum(x.astype(np.int16), 256 - x.astype(np.int16)).sum(axis=1) for x in cands])
    pick = cost.argmin(axis=0)
    rows = np.stack(cands)[pick, np.arange(h)]
    data = np.concatenate([pick.astype(np.uint8)[:, None], rows], axis=1).tobytes()

    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(data, 9)) + chunk(b"IEND", b""))


def write_png(path, arr):
    data = png_bytes(arr)
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


# ===== 沃罗诺伊的“边图”：把贴图里的铅条 / 单元边界还原成可以走的几何 =====
class VoronoiGraph:
    """voronoi_tile(cells, jitter, seed) 的同一组种子，求出每个单元的多边形，再合并成环面上的顶点 / 边图。
    顶点坐标是周期单位（贴图 = 1）的局部坐标 [0,1)²；adj[v] = [(w, (dx, dy))...]，(dx, dy) 是沿这条边走过去的位移
    （不折回周期，所以可以连续走出贴图边界，在世界空间里一直延伸）。"""

    def __init__(self, cells, jitter, seed):
        rng = np.random.default_rng(seed)
        jx, jy = rng.random((cells, cells)), rng.random((cells, cells))

        def seed_pos(i, j):
            ii, jj = i % cells, j % cells
            return np.array([(i + 0.5 + jitter * (jx[ii, jj] - 0.5)) / cells, (j + 0.5 + jitter * (jy[ii, jj] - 0.5)) / cells])

        verts = {}          # 量化后的局部坐标 → 顶点编号
        self.pos = []       # 局部坐标（周期单位）
        self.adj = []
        edge_seen = set()

        def vid(p):
            lx, ly = p[0] % 1.0, p[1] % 1.0
            key = (int(round(lx * 1e5)) % 100000, int(round(ly * 1e5)) % 100000)
            if key not in verts:
                verts[key] = len(self.pos)
                self.pos.append((lx, ly))
                self.adj.append([])
            return verts[key]

        half = 1.6 / cells
        for ci in range(cells):
            for cj in range(cells):
                s = seed_pos(ci, cj)
                poly = [s + np.array(d) for d in ((-half, -half), (half, -half), (half, half), (-half, half))]
                for di in range(-3, 4):
                    for dj in range(-3, 4):
                        if di == 0 and dj == 0:
                            continue
                        b = seed_pos(ci + di, cj + dj)
                        n = b - s
                        mid = (s + b) / 2
                        out = []
                        for k in range(len(poly)):
                            p, q = poly[k], poly[(k + 1) % len(poly)]
                            dp, dq = np.dot(p - mid, n), np.dot(q - mid, n)
                            if dp <= 0:
                                out.append(p)
                            if (dp < 0 < dq) or (dq < 0 < dp):
                                out.append(p + (q - p) * (dp / (dp - dq)))
                        poly = out
                        if len(poly) < 3:
                            break
                    if len(poly) < 3:
                        break
                for k in range(len(poly)):
                    p, q = poly[k], poly[(k + 1) % len(poly)]
                    a, b_ = vid(p), vid(q)
                    if a == b_:
                        continue
                    d = q - p
                    # 去重：同一条边在相邻两个单元里各出现一次（方向相反）；用 (顶点对, |位移|) 区分
                    key = (min(a, b_), max(a, b_), round(abs(float(d[0])), 4), round(abs(float(d[1])), 4))
                    if key in edge_seen:
                        continue
                    edge_seen.add(key)
                    self.adj[a].append((b_, (float(d[0]), float(d[1]))))
                    self.adj[b_].append((a, (-float(d[0]), -float(d[1]))))

    def walk(self, rng, start, length, straight=0.72):
        """从顶点 start 随机游走 length 步（不回头；straight 的概率选转角更小的那条边，走线更像“总线”）。
        返回绝对坐标折线 [(x, y)...]（周期单位，起点用 start 的局部坐标）。"""
        p = np.array(self.pos[start], dtype=float)
        pts = [tuple(p)]
        v, prev, heading = start, -1, None
        for _ in range(length):
            opts = [(w, np.array(d)) for w, d in self.adj[v] if w != prev]
            if not opts:
                break
            if heading is not None and len(opts) > 1 and rng.random() < straight:
                opts.sort(key=lambda o: -float(np.dot(o[1], heading)) / (np.linalg.norm(o[1]) + 1e-9))
                w, d = opts[0]
            else:
                w, d = opts[rng.integers(len(opts))]
            heading = d / (np.linalg.norm(d) + 1e-9)
            p = p + d
            pts.append((float(p[0]), float(p[1])))
            prev, v = v, w
        return pts
