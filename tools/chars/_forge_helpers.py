"""莫德雷德 / 沃尔特共用的私有助手（只在 tools/chars 内使用，不改 kit）。

- utube：带 UV 的管道（kit.core.tube 不生成 UV，贴图只会采到一个像素）
- suit_*_uv：带 UV 的紧身衣躯干 / 四肢（锁子甲等贴图需要 UV）
- pauldron_lames / gorget_lite：kit 同名部件的可控面数版（kit 版固定细分一级，面数偏高）
- 程序化贴图：锻打铸铁、锁子甲、炉膛煤床、焦灼罩袍、刃面符文、风暴闪电纹
- RaggedPanel：下摆带破边尖角的片状垂饰
- 姿态辅助：马步 / 弓步、手臂 IK、垂饰避膝（在骨盆局部坐标里计算，骨盆前倾时也不穿膝）
- tri_report：构建后按材质统计三角面，便于控制预算
- ensure_uv：给无 UV 的部件补空 UV 层，规避 kit 合并网格后贴图失效的问题
"""

import math

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from kit.core import (GLYPHS, TAU, Canvas, _finish, axis_ref, box_blur, catmull, chain, clamp, finish, garment,
                      hash01, height_normal, invdist, lerp, orient, rigid, surface, trim, tube, vfade, voronoi)
from kit.garment import Panel, tail_weight
from kit.motion import Legs


# ===== 网格 =====
def utube(name, points, radii, mats, n=16, per=6, fx=1.0, fy=1.0, up=(0, 0, 1), uv=(1.0, 1.0), texel=None):
    """带 UV 的管道：u 绕圈、v 沿弧长；两端开口（半径为 0 的端点合并成尖）。texel 为每次贴图重复的米数。"""
    pts, rad = catmull(points, radii, per) if per > 1 else ([Vector(p) for p in points], list(radii))
    m = len(pts)
    tangents = [(pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(m)]
    upv = Vector(up)
    n0 = upv - tangents[0] * upv.dot(tangents[0])
    if n0.length < 1e-5:
        n0 = Vector((1, 0, 0)) - tangents[0] * tangents[0].x
    normals = [n0.normalized()]
    for i in range(1, m):
        nn = normals[-1] - tangents[i] * normals[-1].dot(tangents[i])
        normals.append(nn.normalized() if nn.length > 1e-6 else normals[-1])
    cum = [0.0]
    for i in range(1, m):
        cum.append(cum[-1] + (pts[i] - pts[i - 1]).length)
    total = max(cum[-1], 1e-6)
    if texel:
        mean_r = sum(rad) / len(rad) * (fx + fy) / 2
        uv = (max(1, round(TAU * mean_r / texel)), total / texel)

    def fn(u, v):
        j = int(round(v * (m - 1)))
        a = u * TAU
        b = tangents[j].cross(normals[j])
        r = max(rad[j], 1e-6)
        return pts[j] + normals[j] * (math.cos(a) * r * fx) + b * (math.sin(a) * r * fy)
    obj = surface(name, fn, n, m, mats, closed_u=True,
                  uvfn=lambda u, v: (u * uv[0], cum[int(round(v * (m - 1)))] / total * uv[1]))
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def suit_torso_uv(ctx, B, mat, texel=0.7, nu=40, nv=24):
    """紧身衣躯干（带 UV，按 texel 米重复一次贴图）+ 颈管。"""
    z0, z1 = B.torso[-1][0], B.torso[0][0]
    rx, ry, _ = B.torso_r(B.z(1.40))
    ur = max(1, round(math.pi * (rx + ry) / texel))
    vr = (z0 - z1) / texel
    body = surface(f"{ctx.title} torso", lambda u, v: B.torso_point(u * TAU, lerp(z0, z1, v)), nu, nv, [mat],
                   closed_u=True, uvfn=lambda u, v: (u * ur, (1 - v) * vr))
    orient(body, axis_ref)
    ctx.part(body, invdist(["Pelvis", "Spine", "Chest", "Neck"]))
    neck = tube(f"{ctx.title} neck", [(0, 0, B.neck_base - 0.02 * B.s), (0, 0.006 * B.s, B.chin),
                                      (0, 0.012 * B.s, B.chin + 0.06 * B.s)],
                [0.052 * B.s, 0.044 * B.s, 0.042 * B.s], [mat], n=16)
    ctx.part(neck, invdist(["Chest", "Neck", "Head"]))
    return body


def suit_arm_uv(ctx, B, side, label, mat, r=(0.046, 0.050, 0.043, 0.036, 0.028), texel=0.7):
    a = B.arms[label]
    s = B.s * B.limb
    mid = (a["shoulder"] + a["elbow"]) / 2
    arm = utube(f"{ctx.title} arm {label}", [a["inner"], a["shoulder"], mid, a["elbow"], a["wrist"]],
                [x * s for x in r], [mat], n=18, texel=texel)
    ctx.part(arm, chain([f"UpperArm.{label}", f"Forearm.{label}", f"Hand.{label}"], "Chest", 0.05))
    return arm


def suit_leg_uv(ctx, B, side, label, mat, r=(0.088, 0.080, 0.062, 0.060, 0.050, 0.040), texel=0.7):
    L = B.legs[label]
    s = B.s * B.limb
    hip, knee, ankle = L["hip"], L["knee"], L["ankle"]
    top = hip + Vector((0, 0, 0.05 * B.s))
    pts = [top, hip.lerp(knee, 0.35), knee, knee.lerp(ankle, 0.3), knee.lerp(ankle, 0.7), ankle]
    leg = utube(f"{ctx.title} leg {label}", pts, [x * s for x in r], [mat], n=20, texel=texel)
    ctx.part(leg, chain([f"Thigh.{label}", f"Shin.{label}", f"Foot.{label}"], "Pelvis", 0.06))
    return leg


def pauldron_lames(ctx, B, side, label, lames, radius=0.11, spread=1.32, rise=1.18, tilt=0.30, ridge=0.0,
                   thick=0.007, trim_mat=None, trim_r=0.0026, nu=34, nv=9, sub=0, offset=(0, 0, 0), spire=None):
    """分层肩甲（kit.humanoid.pauldron 的可控面数版）。
    lames 为 [(theta0, theta1, shrink, 材质, Chest 权重), ...]：每片单独蒙皮，上片跟躯干、下片跟上臂，
    抬臂时上片不会顶进头盔。spire=(高度, 位置 u, 方向) 只加在首片。返回 (lp(k, u, t), 肩心)。"""
    s = B.s
    shoulder = B.arms[label]["shoulder"] + Vector((0, 0.001, 0.02 * s)) + Vector(offset) * s

    def lp(k, u, t):
        th0, th1, shrink = lames[k][:3]
        rr = radius * s * shrink
        phi = u * spread
        taper = 1 - abs(u) ** 2.6
        mid, half = (th0 + th1) / 2, (th1 - th0) / 2
        th = mid + (t - 0.5) * 2 * half * taper
        d = Vector((math.cos(phi) * math.sin(th) * side, math.sin(phi) * math.sin(th) * rise, math.cos(th)))
        p = shoulder + d * rr * (1 + 0.06 * (1 - abs(u)) + ridge * math.exp(-(u / 0.12) ** 2))
        if k == 0 and spire:
            sp = spire[0] * s * math.exp(-((u - spire[1]) / 0.20) ** 2) * (1 - t) ** 2.0
            p += Vector((side * spire[2][0], spire[2][1], spire[2][2])).normalized() * sp
        return shoulder + Matrix.Rotation(side * tilt, 3, "Y") @ (p - shoulder)
    for k, (th0, th1, shrink, mat, cw) in enumerate(lames):
        spec = rigid(("Chest", cw), (f"UpperArm.{label}", 1 - cw))
        lame = surface(f"{ctx.title} pauldron {label}{k}", lambda u, v, k=k: lp(k, 2 * u - 1, v), nu, nv, [mat])
        orient(lame, lambda c: shoulder)
        ctx.part(finish(lame, thick * s, 0, sub), spec)
        if trim_mat:
            edge = [lp(k, 2 * i / 40 - 1, 1.0) for i in range(41)]
            edge = [p + (p - shoulder).normalized() * 0.004 * s for p in edge]
            ctx.part(trim(f"{ctx.title} pauldron {label}{k} trim", edge, trim_r * s, trim_mat), spec)
    return lp, shoulder


def gorget_lite(ctx, B, mat, trim_mat=None, layers=((1.645, 1.695, 0.090, 0.070), (1.685, 1.735, 0.072, 0.056)),
                nu=40, trim_r=0.0022):
    """护颈（kit.humanoid.gorget 的无细分版）。"""
    s = B.s
    for k, (z0, z1, r0, r1) in enumerate(layers):
        z0, z1 = B.z(z0), B.z(z1)

        def g(u, v, z0=z0, z1=z1, r0=r0 * s, r1=r1 * s):
            a = u * TAU
            z = lerp(z0, z1, v) - 0.018 * s * max(0.0, math.cos(a)) ** 4 * (1 - v)
            r = lerp(r0, r1, v)
            return Vector((r * math.sin(a), 0.004 * s + 0.006 * s * v + r * math.cos(a) * 0.92, z))
        obj = surface(f"{ctx.title} gorget {k}", g, nu, 6, [mat], closed_u=True)
        orient(obj, axis_ref)
        ctx.part(finish(obj, 0.005 * s, 1, 0), invdist(["Chest", "Neck"]))
        if trim_mat:
            rim = [g(i / nu, 1.0) for i in range(nu)]
            rim = [p + Vector((p.x, p.y - 0.004 * s, 0)).normalized() * 0.006 * s for p in rim]
            ctx.part(trim(f"{ctx.title} gorget {k} trim", rim, trim_r * s, trim_mat, closed=True),
                     invdist(["Chest", "Neck"]))


def axis_frame(base, axis):
    """局部 Z 轴对齐 axis、原点在 base 的 4x4 变换（车削体 / 线圈等立式部件用）。"""
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return Matrix.Translation(Vector(base)) @ q.to_matrix().to_4x4()


# ===== 程序化贴图 =====
def noise(shape, r, rng):
    """归一化低频噪声（标准差约 0.5），r 为模糊半径（像素）。"""
    n = box_blur(rng.random(shape).astype(np.float32), r)
    n = n - n.mean()
    return n / (n.std() + 1e-6) * 0.5


def hblur(a, r):
    """只沿横向（u 方向）的盒式模糊，用于拉丝纹。"""
    for _ in range(2):
        c = np.cumsum(np.pad(a, [(0, 0), (r + 1, r)], mode="wrap"), axis=1)
        a = (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)
    return a


def hammered_maps(base_rgb, size=1024, seed=3, cells=18, scorch=0.5, dent=5.0, ridge_rgb=(0.10, 0.07, 0.05),
                  pits=0.0025):
    """锻打铸铁：Voronoi 锤击凹坑 + 细锤痕 + 低频焦痕明暗 + 砂眼；锤痕交界处留一道亮棱。返回 (base, None, normal)。"""
    rng = np.random.default_rng(seed)
    f1, f2, idx = voronoi(size, cells, rng)
    g1, _, _ = voronoi(size, cells * 3, rng)
    grain = box_blur(rng.random((size, size)).astype(np.float32), 1) - 0.5
    pit = box_blur((rng.random((size, size)) < pits).astype(np.float32), 1) * 4.0
    height = np.clip(f1, 0, 1) ** 1.5 * 0.9 + np.clip(g1, 0, 1) ** 1.5 * 0.25 + grain * 0.06 - pit * 0.5
    low = noise((size, size), 40, rng)
    cellv = np.sin(idx * 2.3) * 0.5 + 0.5
    tone = (1.0 + low * scorch * 2.0 + (cellv - 0.5) * 0.35 + grain * 0.4) * (1 - np.clip(pit, 0, 1) * 0.6)
    ridge = np.clip(1 - (f2 - f1) / 0.07, 0, 1) ** 2
    base = np.stack([base_rgb[i] * tone + ridge * ridge_rgb[i] * 0.6 for i in range(3)], axis=2)
    return np.clip(base, 0, 1), None, height_normal(box_blur(height.astype(np.float32), 1), dent)


def mail_maps(base_rgb, size=1024, rings=40, width=0.12, radius=0.44):
    """锁子甲：错行交扣的小铁环（横向 rings 个、纵向 2×rings 行），环顶高光 + 法线凸起。"""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size * rings
    h = np.zeros((size, size), np.float32)
    row0 = np.floor(ys / 0.5)
    for dr in (-1, 0, 1, 2):
        r = row0 + dr
        cy = r * 0.5
        off = (r % 2) * 0.5
        col0 = np.floor(xs - off)
        for dc in (-1, 0, 1):
            cx = col0 + dc + off + 0.5
            d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
            h = np.maximum(h, np.clip(1 - np.abs(d - radius) / width, 0, 1))
    h = h ** 0.6
    base = np.stack([base_rgb[i] * (0.30 + 1.2 * h) for i in range(3)], axis=2)
    return np.clip(base, 0, 1), None, height_normal(box_blur(h, 1), 3.0)


def coal_maps(emit_rgb, size=512, cells=7, seed=2):
    """炉膛煤床：Voronoi 块心炽白、块缝暗红，以自发光为主。返回 (base, emission, normal)。"""
    rng = np.random.default_rng(seed)
    f1, f2, idx = voronoi(size, cells, rng)
    edge = np.clip((f2 - f1) / 0.42, 0, 1)
    cellv = np.sin(idx * 3.1) * 0.5 + 0.5
    heat = np.clip(edge ** 0.75 * (0.55 + 0.45 * cellv) + noise((size, size), 6, rng) * 0.12, 0, 1)
    deep = np.array((0.50, 0.06, 0.01))
    mid = np.array(emit_rgb)
    hot = np.array((1.0, 0.88, 0.62))
    t = heat[..., None]
    col = np.where(t < 0.5, deep + (mid - deep) * (t * 2), mid + (hot - mid) * (t * 2 - 1))
    em = col * (0.2 + 0.8 * t)
    return np.clip(em * 0.4, 0, 1), np.clip(em, 0, 1), height_normal(heat, 2.0)


def scorch_cloth_maps(emit_rgb, base_rgb=(0.085, 0.032, 0.020), w=512, h=1024, seed=8,
                      thread_rgb=(0.36, 0.22, 0.10), glyph_rows=7):
    """焦灼罩袍：粗织纹 + 越往下摆越焦黑、下摆余烬星火 + 两侧刺绣边线 + 中缝一列微光符文（v=0 为下摆）。"""
    rng = np.random.default_rng(seed)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    v = ys / h
    weave = np.sin(xs * TAU / 5) * np.sin(ys * TAU / 5) * 0.5 + 0.5
    n1 = noise((h, w), 10, rng)
    burn = 1 - np.clip((v + n1 * 0.05) / 0.30, 0, 1) ** 1.2
    tone = (0.85 + 0.3 * weave) * (1 + noise((h, w), 30, rng) * 0.35) * (1 - 0.78 * burn)
    base = np.stack([base_rgb[i] * tone for i in range(3)], axis=2)
    # 两侧刺绣边线（双线）
    cv = Canvas(w, h)
    for x in (w * 0.07, w * 0.10, w * 0.90, w * 0.93):
        cv.line(x, h * 0.04, x, h * 0.99, 1)
    border = np.clip(cv.mask, 0, 1)
    base += border[..., None] * np.array(thread_rgb)[None, None, :] * (1 - 0.6 * burn[..., None])
    # 中缝符文列
    gv = Canvas(w, h)
    S = w * 0.16
    for k in range(glyph_rows):
        g = GLYPHS[int(rng.integers(len(GLYPHS)))]
        x0, y0 = w / 2 - S / 2, h * (0.22 + k * 0.10)
        for (a, b, c, d) in g:
            gv.line(x0 + a * S, y0 + b * S, x0 + c * S, y0 + d * S, 2)
        gv.ring(w / 2, y0 + S * 1.35, 4, 1)
    gv.line(w / 2, h * 0.20, w / 2, h * (0.22 + glyph_rows * 0.10), 1)
    glyph = np.clip(gv.mask, 0, 1)
    base += glyph[..., None] * np.array(thread_rgb)[None, None, :] * 0.6
    # 余烬：下摆附近星火 + 焦边暗火
    sp = ((rng.random((h, w)) > 0.9975) & (rng.random((h, w)) < burn ** 2)).astype(np.float32)
    sp = box_blur(sp, 1) * 6.0
    edge = np.clip(1 - v / 0.05 + n1 * 0.5, 0, 1) ** 2
    fire = np.clip(sp + edge * 0.9 + box_blur(glyph, 2) * 0.35 + glyph * 0.45, 0, 1.2)
    em = np.stack([fire * c for c in emit_rgb], axis=2)
    height = weave * 0.25 + border * 0.6 + glyph * 0.5
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(height.astype(np.float32), 1), 1.5)


def blade_maps(emit_rgb, base_rgb=(0.13, 0.125, 0.12), w=1024, h=256, seed=4, band=(0.15, 0.33),
               span=(0.08, 0.60), edge_v=0.80, polish_rgb=(0.52, 0.51, 0.50)):
    """刃面：沿刃长的拉丝纹 + 一条发光符文带（band 为 v 范围、span 为 u 范围）+ 刃口磨亮渐变。"""
    rng = np.random.default_rng(seed)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    v = ys / h
    streak = hblur(rng.random((h, w)).astype(np.float32), 40)
    streak = (streak - streak.mean()) / (streak.std() + 1e-6)
    tone = 1.0 + streak * 0.10 + noise((h, w), 20, rng) * 0.25
    base = np.stack([base_rgb[i] * tone for i in range(3)], axis=2)
    t = np.clip((v - edge_v) / (1 - edge_v), 0, 1)[..., None] ** 1.5
    base = base * (1 - t) + np.array(polish_rgb)[None, None, :] * t
    cv = Canvas(w, h)
    y0, y1 = band[0] * h, band[1] * h
    cv.line(span[0] * w, y0, span[1] * w, y0, 1)
    cv.line(span[0] * w, y1, span[1] * w, y1, 1)
    S = (y1 - y0) * 0.62
    x = span[0] * w + S * 0.4
    while x + S < span[1] * w:
        g = GLYPHS[int(rng.integers(len(GLYPHS)))]
        gy = y0 + (y1 - y0 - S) / 2
        for (a, b, c, d) in g:
            cv.line(x + a * S, gy + b * S, x + c * S, gy + d * S, 2)
        x += S * 1.45
    mask = np.clip(cv.mask, 0, 1)
    glow = np.clip(mask + box_blur(mask, 3) * 0.6, 0, 1)
    em = np.stack([glow * c for c in emit_rgb], axis=2)
    base = base * (1 - mask[..., None] * 0.6)
    height = -mask * 0.8 + streak * 0.01
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(height.astype(np.float32), 1), 1.4)


def lightning_maps(emit_rgb, base_rgb=(0.010, 0.014, 0.032), size=1024, seed=5, bolts=10, reach=(0.40, 0.95),
                   line_rgb=None, fade=True):
    """风暴闪电纹：自下摆（v=0）向上生长的锯齿主干 + 分叉细枝，末端收成小节点（尼克斯电路的风暴变体）。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    step = 9.0

    def bolt(x, y, a, length, w, depth):
        n = int(length / step)
        for i in range(n):
            a2 = a + float(np.clip(rng.normal(0, 0.6), -1.1, 1.1))
            nx, ny = x + math.cos(a2) * step, y + math.sin(a2) * step
            if not (5 < nx < size - 5 and ny < size - 5):
                return
            cv.line(x, y, nx, ny, w)
            x, y = nx, ny
            if depth < 2 and rng.random() < 0.06:
                bolt(x, y, a + rng.choice([-1, 1]) * rng.uniform(0.45, 0.95),
                     length * rng.uniform(0.18, 0.38) * (1 - i / n), max(1, w - 1), depth + 1)
        cv.ring(x, y, 3 + w, 1)
    for x in np.linspace(size * 0.05, size * 0.95, bolts) + rng.uniform(-24, 24, bolts):
        bolt(float(x), 0.0, math.pi / 2, rng.uniform(*reach) * size, 2, 0)
    mask = np.clip(cv.mask, 0, 1)
    f = vfade(size, size, start=0.10, span=0.80) if fade else np.ones_like(mask)
    return _finish(mask, f, rng, emit_rgb, base_rgb, line_rgb or tuple(c * 0.14 for c in emit_rgb))


# ===== 布料 =====
class RaggedPanel(Panel):
    """下摆带破边尖角的片状垂饰：tails 个尖角（长度随机），其余与 kit.garment.Panel 相同（建议 point=0）。"""

    def __init__(self, *args, tails=3, tail_len=0.08, ragged=0.35, seed=1.3, **kw):
        super().__init__(*args, **kw)
        self.tails, self.tail_len, self.ragged, self.seed = tails, tail_len, ragged, seed

    def bottom(self, u):
        k = min(self.tails - 1, int(u * self.tails))
        L = self.tail_len * (1 - self.ragged + 2 * self.ragged * hash01(k, self.seed))
        return self._tip - L * tail_weight(u, self.tails, 0.1)

    def point(self, u, v):
        w = self.width(v)
        x = (u - 0.5) * w
        y = self.side * (self.depth(v) - self.curve * x * x) + self.flutter * math.sin(u * math.pi * 3 + v * 4) * v
        return Vector((self.cx + x, y, lerp(self._top, self.bottom(u), v)))

    def param(self, p):
        u = 0.5
        v = 0.5
        for _ in range(4):
            v = clamp((self._top - p.z) / max(1e-4, self._top - self.bottom(u)))
            u = clamp((p.x - self.cx) / max(1e-4, self.width(v)) + 0.5)
        return u, v

    def hem(self, ctx, name, mat, radius, n=60):
        """沿破边下摆加一道发光滚边。"""
        pts = [self.point(i / (n - 1), 1.0) + Vector((0, self.side * 0.003, 0.002)) for i in range(n)]
        ctx.part(trim(f"{name} hem", pts, radius, mat), garment(self))


# ===== 姿态辅助 =====
def plant_stance(rig, B, pose, lf, rf, sink, yaw_l=0.0, yaw_r=0.0, knee_out=0.2, pitch_l=0.0, pitch_r=0.0):
    """马步 / 弓步：lf、rf 为左右脚踝相对静止位置的偏移 (x, y[, z])（身高系数）；需先写好骨盆 / 脊柱姿态。"""
    legs = Legs(rig, B)
    pose["_hover"] = -sink * B.s
    for label, off, yaw, pitch in (("L", lf, yaw_l, pitch_l), ("R", rf, yaw_r, pitch_r)):
        a = legs.rest[label]["ankle"] + Vector((off[0], off[1], off[2] if len(off) > 2 else 0.0)) * B.s
        legs.plant(pose, label, a, pitch=pitch, yaw=yaw, knee_out=knee_out)


def arm_ik(rig, pose, label, target, pole, hand_dir=None):
    """手臂两段 IK：腕部到达 target，肘朝 pole；静止时肘朝后（rest_pole=-Y），避免上臂滚转。"""
    rig.ik2(pose, f"UpperArm.{label}", f"Forearm.{label}", Vector(target), Vector(pole),
            rest_pole=Vector((0, -1, 0)))
    if hand_dir is not None:
        rig.aim(pose, f"Hand.{label}", Vector(hand_dir))


def panel_clear(rig, B, pose, panel, extra=0.0, margin=0.075, base=0.04):
    """前 / 后垂饰按膝盖位置外掀：把膝盖换算到骨盆静止坐标里比较，骨盆前倾、深蹲时也不会穿出布面。"""
    ph = rig.head(pose, "Pelvis")
    inv = rig.delta(pose, "Pelvis").inverted()
    rest = rig.SEG["Pelvis"][0]
    need = base
    depth = panel.depth(0.5) + 0.02 * B.s
    for label in ("L", "R"):
        for name in (f"Thigh.{label}", f"Shin.{label}"):
            p = inv @ (rig.tail(pose, name) - ph) + rest if name.startswith("Thigh") else \
                inv @ (rig.head(pose, name).lerp(rig.tail(pose, name), 0.25) - ph) + rest
            ahead = panel.side * p.y
            dz = max(0.2 * B.s, panel._top - p.z)
            need = max(need, math.atan2(ahead + margin * B.s - depth, dz))
    rig.garment_pose(pose, panel, lambda k, j: need + extra)
    return need


def uv_scale(obj, su=1.0, sv=1.0):
    """按比例缩放对象的 UV（修正细长部件上贴图被拉伸）。"""
    for layer in obj.data.uv_layers:
        for d in layer.data:
            d.uv = (d.uv[0] * su, d.uv[1] * sv)
    return obj


def ensure_uv(ctx):
    """kit 的 Rig._merge_skinned 以同材质第一个部件为活动对象合并；若它没有 UV 层（kit 的 tube / ellipsoid 都不带 UV），
    合并结果里的 UVMap 既不是活动层也不是渲染层，整张材质的贴图会退化成单色。给所有无 UV 的部件补一层全零 UV。"""
    for obj in [o for o, _ in ctx.parts] + [a[0] for a in ctx.attached] + list(ctx.hidden):
        if obj.type == "MESH" and not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap", do_init=False)


def tri_report(ctx):
    """按首材质统计三角面（构建结束时调用，面数预算参考）。"""
    per, hidden = {}, 0
    for obj in [o for o, _ in ctx.parts] + [a[0] for a in ctx.attached] + list(ctx.hidden):
        n = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        key = obj.data.materials[0].name if obj.data.materials else "?"
        per[key] = per.get(key, 0) + n
        if obj in ctx.hidden:
            hidden += n
    total = sum(per.values())
    print("TRIS ESTIMATE", total, "hidden", hidden,
          {k: v for k, v in sorted(per.items(), key=lambda kv: -kv[1])})
    return total
