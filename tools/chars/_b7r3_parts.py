"""Boss 7（灰烬炽天使）第三轮私有部件：不改 kit 与其他配方，缺的东西在这里复制 / 新写。

- 贴图：嵌金卷草暗钢（inlay_maps）、金边羽甲（petal_maps）、鎏金雕花（gilded_maps）。
- 半透明火焰：沿用 _b2r2_parts 的 flame_sheets / flame_material（alphaMode=BLEND、双面），这里只包一层 RGBA 配色。
- 部件：花瓣肩甲（petal）、鳞片领甲、飘带（banner）、余烬碎片与灰羽、金色火冠辐条等。
"""

import math
import random

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from kit.core import (TAU, Canvas, bm_object, box_blur, clamp, finish, height_normal, lerp, orient, smoothstep,
                      surface, tube, voronoi)

from chars._b2r2_parts import flame_material, flame_maps as sheet_maps, flame_sheets   # noqa: F401


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ===== 贴图 =====
def inlay_maps(base_rgb, gold_rgb, size=1024, seed=31, dimples=14, density=5, line=2, tone=1.0):
    """嵌金卷草暗钢：锻打凹坑明暗 + 每格一套“框线 + 双向卷草 + 菱形芯”的暗金嵌线（线比 forged_maps 粗、金色更亮）。
    返回 (base, None, normal)。"""
    rng = np.random.default_rng(seed)
    f1, _, idx = voronoi(size, dimples, rng)
    cellv = np.sin(idx * 1.9 + seed) * 0.5 + 0.5
    cloud = box_blur(rng.random((size, size)).astype(np.float32), 30) - 0.5
    grain = box_blur(rng.random((size, size)).astype(np.float32), 1) - 0.5
    cv = Canvas(size, size)
    cell = size / density
    for gx in range(density):
        for gy in range(density):
            cx, cy = (gx + 0.5) * cell, (gy + 0.5) * cell
            # 内框：四角切角的矩形
            m, c = cell * 0.12, cell * 0.10
            x0, y0, x1, y1 = gx * cell + m, gy * cell + m, (gx + 1) * cell - m, (gy + 1) * cell - m
            for a, b in (((x0 + c, y0), (x1 - c, y0)), ((x1, y0 + c), (x1, y1 - c)), ((x1 - c, y1), (x0 + c, y1)),
                         ((x0, y1 - c), (x0, y0 + c)), ((x0 + c, y0), (x0, y0 + c)), ((x1 - c, y0), (x1, y0 + c)),
                         ((x1, y1 - c), (x1 - c, y1)), ((x0, y1 - c), (x0 + c, y1))):
                cv.line(a[0], a[1], b[0], b[1], line)
            # 双向卷草
            for flip in (1, -1):
                t = np.linspace(0, rng.uniform(1.3, 1.8) * TAU, 80)
                r = cell * 0.27 * np.exp(-0.21 * t)
                ph = rng.uniform(0, TAU)
                ox = cx + flip * cell * 0.17
                xs = ox + flip * r * np.cos(t + ph)
                ys = cy + r * np.sin(t + ph)
                for i in range(len(t) - 1):
                    cv.line(xs[i], ys[i], xs[i + 1], ys[i + 1], line)
            # 菱形芯
            d = cell * 0.055
            for a, b in (((cx, cy - d), (cx + d, cy)), ((cx + d, cy), (cx, cy + d)), ((cx, cy + d), (cx - d, cy)),
                         ((cx - d, cy), (cx, cy - d))):
                cv.line(a[0], a[1], b[0], b[1], max(1, line - 1))
    mask = np.clip(box_blur(cv.mask, 1) * 1.4, 0, 1)
    shade = 0.80 + 0.26 * cellv + 0.30 * (f1 - 0.35) + cloud * 1.4 + grain * 0.10
    base = np.array(base_rgb)[None, None, :] * shade[..., None]
    gold = np.array(gold_rgb)[None, None, :] * (0.85 + 0.3 * (box_blur(rng.random((size, size)).astype(np.float32), 4)
                                                               - 0.5) * 2)[..., None] * tone
    base = base * (1 - mask[..., None]) + gold * mask[..., None]
    hgt = np.clip(f1, 0, 0.8) ** 2 * 0.9 - mask * 0.6
    return np.clip(base, 0, 1), None, height_normal(box_blur(hgt.astype(np.float32), 1), 2.0)


def petal_maps(base_rgb, gold_rgb, emit_rgb=None, size=512, seed=5, barbs=7.0, border=0.10, glow=0.0):
    """羽甲 / 花瓣甲片贴图（u 横跨宽度、v 自根部 0 到尖端 1）：暗钢底 + 金色宽边 + 金色中脊 + 向尖端斜出的金色羽枝线；
    glow>0 时中脊与羽枝同时发一点余烬光。"""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    x = np.abs(2 * u - 1)
    edge = np.maximum(sstep(1 - border, 1 - border * 0.7, x), sstep(0.93, 0.965, v))
    rib = np.exp(-(x / 0.045) ** 2) * sstep(0.04, 0.12, v)
    phase = (v * barbs + x * 1.15) % 1.0
    barb = np.exp(-((phase - 0.5) / 0.055) ** 2) * sstep(0.10, 0.28, x) * (1 - sstep(0.80, 0.92, x)) * \
        sstep(0.10, 0.2, v) * (1 - sstep(0.88, 0.95, v))
    gold_m = np.clip(np.maximum(edge, np.maximum(rib, barb * 0.85)), 0, 1)
    cloud = box_blur(rng.random((size, size)).astype(np.float32), 24) - 0.5
    grain = box_blur(rng.random((size, size)).astype(np.float32), 1) - 0.5
    shade = 0.85 + cloud * 0.8 + grain * 0.15
    base = np.array(base_rgb)[None, None, :] * shade[..., None]
    gold = np.array(gold_rgb)[None, None, :] * (0.9 + 0.2 * (grain * 4))[..., None]
    base = base * (1 - gold_m[..., None]) + gold * gold_m[..., None]
    em = None
    if emit_rgb is not None and glow > 0:
        g = np.clip(rib * 0.9 + barb * 0.5, 0, 1) * glow
        em = np.stack([g * c for c in emit_rgb], axis=2)
    hgt = edge * 0.6 + rib * 0.5 + barb * 0.25
    return np.clip(base, 0, 1), em, height_normal(box_blur(hgt.astype(np.float32), 1), 1.6)


def gilded_maps(gold_rgb, groove_rgb, size=1024, seed=19, density=8, width=2):
    """鎏金雕花：金底 + 暗色卷草沟槽（kit.filigree_maps 的加粗版，沟槽更深、金面带细微锻打明暗）。"""
    from kit.core import filigree_maps
    base, em, nrm = filigree_maps(gold_rgb, groove_rgb, None, size=size, seed=seed, density=density, width=width)
    rng = np.random.default_rng(seed + 3)
    cloud = box_blur(rng.random((size, size)).astype(np.float32), 22) - 0.5
    base = np.clip(base * (1 + cloud[..., None] * 0.5), 0, 1)
    return base, None, nrm


# ===== 半透明火焰（RGBA 薄片） =====
def flame_mats(M, title, strength_out=3.0, strength_in=3.6):
    """外焰深红橙、内焰黄白两张半透明材质，登记为 M["sflame"] / M["score"]（名字含 flame / core，游戏版不减面）。"""
    M["sflame"] = flame_material(f"{title} terminal flame sheet", sheet_maps(128, seed=3, core=0.9), strength_out)
    M["score"] = flame_material(f"{title} flame core sheet",
                                sheet_maps(128, seed=5, hot=(1.0, 0.95, 0.70), mid=(1.0, 0.66, 0.22),
                                           edge=(1.0, 0.36, 0.06), core=1.5), strength_in)
    return M["sflame"], M["score"]


def fire(name, base, direction, height, width, M, n=3, seed=0.0, lean=0.0, nu=2, nv=8, core=True):
    """一束火舌：外焰薄片 + 内焰薄片（更短更窄）。返回对象列表。"""
    out = [flame_sheets(f"{name} flame", base, direction, height, width, [M["sflame"]], n=n, seed=seed, nu=nu,
                        nv=nv, lean=lean)]
    if core:
        out.append(flame_sheets(f"{name} flame core", base, direction, height * 0.58, width * 0.52, [M["score"]],
                                n=max(2, n - 1), seed=seed + 4.1, nu=nu, nv=nv, lean=lean * 0.6))
    return out


# ===== 肩甲花瓣 =====
def petal_surface(name, shoulder, side, rr, phi_c, half, th_a, th_b, rise, tilt, mats, lift=0.08, curl=0.14,
                  nu=7, nv=13, thick=0.012, flare=0.0):
    """球面上的一片长花瓣（肩甲羽片）：沿极角 th_a→th_b 由根到尖，宽度 half(弧度，半宽) 向尖端收窄成钝尖；
    球坐标与 _b7_lib.pauldron_lite 同一套（d = (cosφ·sinθ·side, sinφ·sinθ·rise, cosθ)），尖端向外卷 curl。
    返回 (对象, 取点函数 pt(x∈[-1,1], v∈[0,1]))。UV：u 横跨、v 根→尖。"""
    rot = Matrix.Rotation(side * tilt, 3, "Y")

    def pt(x, v):
        w = half * (1 - v ** 2.3) ** 0.75 * (0.62 + 0.38 * smoothstep(0.0, 0.22, v))
        phi = phi_c + x * w
        th = lerp(th_a, th_b, v)
        d = Vector((math.cos(phi) * math.sin(th) * side, math.sin(phi) * math.sin(th) * rise, math.cos(th)))
        r = rr * (1 + lift * (1 - 0.8 * x * x) * math.sin(math.pi * min(1.0, v * 0.9 + 0.1)) + curl * v ** 2.6 + flare * v)
        return shoulder + rot @ (d * r)
    obj = surface(name, lambda u, v: pt(2 * u - 1, v), nu, nv, mats, uvfn=lambda u, v: (u, v))
    orient(obj, lambda c: shoulder)
    return finish(obj, thick, 0, 0), pt


# ===== 余烬与灰羽 =====
def shard(name, center, size, mats, seed=0.0, flat=0.32):
    """余烬碎片：扁平的不规则菱形片（6 个顶点 × 2 面，十几个三角面），刚性挂骨。"""
    rnd = random.Random(int(seed * 977) + 3)
    c = Vector(center)
    a = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized()
    b = a.orthogonal().normalized()
    n = a.cross(b)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    ring = []
    for k in range(5):
        ang = k / 5 * TAU + rnd.uniform(-0.25, 0.25)
        rr = size * rnd.uniform(0.55, 1.0) * (1.5 if k == 0 else 1.0)
        ring.append(bm.verts.new(c + (a * math.cos(ang) + b * math.sin(ang)) * rr))
    top = bm.verts.new(c + n * size * flat)
    bot = bm.verts.new(c - n * size * flat)
    for k in range(5):
        k2 = (k + 1) % 5
        for apex in (top, bot):
            tri = (ring[k], ring[k2], apex) if apex is top else (ring[k2], ring[k], apex)
            f = bm.faces.new(tri)
            for lp in f.loops:
                lp[uvl].uv = (0.5, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats, smooth=False)


# ===== UV 工具 =====
def scale_uv(obj, su, sv):
    """把对象的 UV 按 (su, sv) 缩放（贴图重复 su × sv 次）：kit 曲面默认 UV 是 0..1 铺满整块，大件上的雕花会被拉成巨大的纹样。"""
    uv = obj.data.uv_layers[0].data
    arr = np.empty(len(uv) * 2, np.float32)
    uv.foreach_get("uv", arr)
    arr = arr.reshape(-1, 2)
    arr[:, 0] *= su
    arr[:, 1] *= sv
    uv.foreach_set("uv", arr.ravel())
    return obj


def find_part(ctx, name):
    for o, *_ in ctx.parts:
        if o.name == name or o.name.startswith(name + "."):
            return o
    return None


def shell2(ctx, B, name, zt, zb, grow, mat, spec, a0=0.0, a1=TAU, thick=0.008, nu=72, nv=24, shape=None, tile=1.2):
    """贴合躯干的甲壳（改写 kit.humanoid.shell）：UV 按弧长 / 高度折算成米（tile 米一张贴图），
    雕花大小在大件上也保持一致。zt/zb 为高度常数或 f(a)。返回 pt(u, v)。"""
    full = abs(a1 - a0 - TAU) < 1e-6
    zt_f = zt if callable(zt) else (lambda a: zt)
    zb_f = zb if callable(zb) else (lambda a: zb)

    def pt(u, v):
        a = a0 + u * (a1 - a0)
        z = lerp(zt_f(a), zb_f(a), v)
        g = grow + (shape(a, z) if shape else 0.0)
        return B.torso_point(a, z, g)
    zm = (zt_f(0.0) + zb_f(0.0)) / 2
    rx, ry, _ = B.torso_r(zm)
    perim = (a1 - a0) * math.sqrt((rx * rx + ry * ry) / 2)
    height = abs(zt_f(0.0) - zb_f(0.0)) + 0.01
    obj = surface(name, pt, nu, nv, [mat], closed_u=full,
                  uvfn=lambda u, v: (u * perim / tile, (1 - v) * height / tile))
    orient(obj, lambda c: Vector((0, 0, c.z)))
    ctx.part(finish(obj, thick, 1, 0), spec)
    return pt


# ===== 羽毛 =====
def plume_width(t):
    """阔羽宽度系数：根部细柄 → 很快展到满宽 → 保持 → 圆润收尖（比 _b7_lib.feather_width 的“长矛”饱满得多）。"""
    if t < 0.20:
        return 0.30 + 0.70 * math.sin(math.pi / 2 * t / 0.20)
    if t < 0.60:
        return 1.0 - 0.05 * (t - 0.20) / 0.40
    x = (t - 0.60) / 0.40
    return max(0.0, (1 - x ** 2.1) ** 0.72) * 0.95


def plume_maps(emit_rgb, root_rgb, mid_rgb, tip_rgb, gold_rgb, size=1024, seed=5, barbs=44, edge=0.20, tip=0.46,
               heat=1.0, hot_rgb=(1.0, 0.82, 0.50), deep_rgb=(0.52, 0.07, 0.02), rib=0.9, rib_w=0.05, ambient=0.0):
    """第三轮刃羽（配合 ridge_blade 的 UV：u 沿羽长、v 沿宽度，中脊 v=0.5）：
    羽根灰烬黑 → 羽身暖炭灰 → 羽尖炭灰；羽枝细纹明显；金色中脊（根部起、近尖端渐隐）；
    两侧刃口与羽尖烧成炽热渐变（暗红 → 橙 → 金白），发光带自根向尖变宽、边缘锯齿不规则；零星火星。"""
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
    chips = box_blur((rng.random((size, size)) > 0.998).astype(np.float32), 2) * 25 * sstep(0.3, 0.9, u)
    k1 = sstep(0.0, 0.55, hf)[..., None]
    k2 = sstep(0.55, 1.0, hf)[..., None]
    ramp = np.array(deep_rgb)[None, None, :] * (1 - k1) + np.array(emit_rgb)[None, None, :] * k1
    ramp = ramp * (1 - k2) + np.array(hot_rgb)[None, None, :] * k2
    glow = np.clip(hf ** 1.05 + np.clip(chips, 0, 1) * 0.6, 0, 1.2)
    em = ramp * glow[..., None] * heat
    if ambient > 0:      # 第四轮：整片羽面一层极淡的暗红余烬底光——冷色逆光下背面也读成“灰烬黑带暖光”，不再泛灰蓝
        em = em + np.array(deep_rgb)[None, None, :] * (ambient * (0.55 + 0.45 * barb))[..., None]
    col = np.array(root_rgb)[None, None, :] * (1 - t1[..., None]) + np.array(mid_rgb)[None, None, :] * t1[..., None]
    col = col * (1 - t2[..., None] * 0.6) + np.array(tip_rgb)[None, None, :] * t2[..., None] * 0.6
    base = col * (0.78 + 0.22 * barb[..., None] + noise[..., None] * 0.25 + cloud[..., None] * 1.0)
    base = base * (1 - 0.45 * hf[..., None]) + ramp * hf[..., None] * 0.16
    gold = np.array(gold_rgb)[None, None, :]
    base = base * (1 - spine[..., None] * rib) + gold * spine[..., None] * rib
    hgt = barb * 0.25 + spine * 0.8 - hf * 0.2
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(hgt.astype(np.float32), 1), 2.0)


# ===== 圣光日轮（光环背后的半透明放射光盘） =====
def aura_maps(size=256, rays=28, hot=(1.0, 0.92, 0.66), mid=(1.0, 0.74, 0.30), edge=(0.92, 0.52, 0.14)):
    """放射光盘贴图（RGBA）：u 绕一圈（重复 rays 道光芒）、v 自圆心 0 到边缘 1；alpha = 光芒条纹 × 径向衰减，
    圆心偏金白、向外橙红；最外缘一圈细亮环。"""
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    ray = 0.5 + 0.5 * np.cos(TAU * u * rays)
    ray = ray ** 2.2
    wide = 0.5 + 0.5 * np.cos(TAU * (u * 7 + 0.3))
    fall = np.clip(1 - v, 0, 1) ** 0.75 * sstep(0.04, 0.22, v)
    ring = np.exp(-((v - 0.965) / 0.018) ** 2) * 0.9
    alpha = np.clip(fall * (0.20 + 0.80 * ray) * (0.60 + 0.40 * wide) * 0.62 * (0.55 + 0.45 * sstep(0.30, 0.70, v)) + ring * 0.45, 0, 1)
    t = np.clip(1 - v * 1.15, 0, 1)
    c0, c1, c2 = (np.array(c, np.float32)[None, None, :] for c in (edge, mid, hot))
    lo = np.clip(t * 2, 0, 1)[..., None]
    hi = np.clip(t * 2 - 1, 0, 1)[..., None]
    rgb = (c0 * (1 - lo) + c1 * lo) * (1 - hi) + c2 * hi
    return np.concatenate([rgb, alpha[..., None]], axis=2).astype(np.float32)


def aura_disc(name, center, au, av, radius, mats, nu=56, nv=4):
    """放射光盘网格：圆心在 center，盘面由 au / av 张成；UV：u 绕一周、v 自圆心 0 到边缘 1。"""
    c = Vector(center)
    au, av = Vector(au), Vector(av)

    def pt(u, v):
        a = u * TAU
        return c + (au * math.sin(a) + av * math.cos(a)) * (radius * v)
    obj = surface(name, pt, nu, nv, mats, closed_u=True, uvfn=lambda u, v: (u, v))
    return obj
