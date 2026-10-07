"""Boss 7（灰烬炽天使）第五轮：胸口“终末圣心”改形——刻面红宝石取代扑克红心。

保留：金框、荆棘藤（连刺）、两侧环抱的鎏金羽片、金链、心尖金泪滴；
改动：
- 中间的心由“渐变贴图的粉橙心形宝石”改成多刻面红宝石：九边不规则切面轮廓（左右不对称、整体微倾），
  玫瑰式切割（腰圈 → 星形刻面 → 冠部刻面 → 台面），平面着色，每个刻面按“环位置 + 朝向光源的程度”分到
  热橙 / 红橙 / 深红三档自发光材质，读成“内部燃烧的宝石”；三档材质都不带发光贴图（游戏里名字含 heart / glow，
  辉光权重 0.5，圣心是四个主发光区之一）；
- 心板、金框、内框、荆棘藤随新轮廓走（金框仍是包住宝石的金色镶口，不再是标准心形）。
"""

import math
import random

import bmesh
import bpy
from mathutils import Vector

from kit.core import invdist, lerp, rigid, spike, tube

from chars._b7_lib import rim
from chars._b7r4_parts import chain_swag, torso_feather, weld


# 九边不规则切面轮廓（x 向右、z 向上，归一化到约 ±1；逆时针；左右不对称：右肩高、左下斜、底尖偏左）
GEM_POLY = [(-0.34, 0.96), (0.40, 1.00), (0.90, 0.58), (1.00, 0.00), (0.58, -0.52), (0.04, -1.04),
            (-0.62, -0.50), (-1.00, 0.04), (-0.86, 0.56)]
TILT = math.radians(-8.0)                 # 整体向右微倾（顺时针）


def _rot(p, a=TILT):
    ca, sa = math.cos(a), math.sin(a)
    return (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca)


def poly_pts():
    return [_rot(p) for p in GEM_POLY]


def chaikin(pts, it=2, cut=0.25):
    """闭合折线的切角细分：每轮每条边取 25% / 75% 两点，轮廓变圆润（镶口金框用）。"""
    for _ in range(it):
        out = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            out.append((lerp(a[0], b[0], cut), lerp(a[1], b[1], cut)))
            out.append((lerp(a[0], b[0], 1 - cut), lerp(a[1], b[1], 1 - cut)))
        pts = out
    return pts


def smooth_outline():
    return chaikin(poly_pts(), 2, 0.25)


def outline_at(pts, u):
    """闭合折线按参数 u∈[0,1) 取点（线性插值）。"""
    n = len(pts)
    f = (u % 1.0) * n
    i = int(f)
    t = f - i
    a, b = pts[i % n], pts[(i + 1) % n]
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))


def outline_dome(name, c, pts, w, h, depth, mats, nu=40, nv=5, power=0.55):
    """穹顶心板（面朝 +Y）：沿新轮廓放射；UV 取轮廓平面投影（熔缝贴图不被拉伸）。"""
    from kit.core import surface, orient
    c = Vector(c)

    def P(u, v):
        x, z = outline_at(pts, u)
        d = depth * max(0.0, 1 - v ** 2.0) ** power
        return c + Vector((x * w * v, d, z * h * v))

    def uv(u, v):
        x, z = outline_at(pts, u)
        return (0.5 + 0.5 * x * v, 0.5 + 0.5 * z * v)
    obj = surface(name, P, nu, nv, mats, closed_u=True, uvfn=uv)
    weld(obj)
    orient(obj, lambda q: c - Vector((0, 0.5, 0)))
    return obj


def outline_ring(c, pts, w, h, y, z0=0.0, scale=1.0):
    c = Vector(c)
    return [Vector((c.x + x * w * scale, y, c.z + z * h * scale + z0)) for x, z in pts]


# ===== 刻面红宝石 =====
def ruby(name, c, w, h, depth, mats, seed=7):
    """玫瑰式切割红宝石（面朝 +Y，底面落在 c 所在平面）：
    腰圈 A（九边轮廓）→ 星形刻面环 B（错半格）→ 冠部环 C（与 A 对位）→ 台面环 D（错半格）→ 平台面。
    mats = (热, 中, 深) 三个发光材质；每个三角刻面按 环位置 + 朝向假想光源（左上前）的程度 分档。"""
    rnd = random.Random(seed)
    c = Vector(c)
    A = poly_pts()
    n = len(A)

    def mid(i, k=1.0):
        a, b = A[i % n], A[(i + 1) % n]
        return ((a[0] + b[0]) / 2 * k, (a[1] + b[1]) / 2 * k)

    def jit(s):
        return 1 + rnd.uniform(-s, s)
    rings = [
        # (z 层 0..1，各点 (x, z) 归一化)
        (0.00, [(x, z) for x, z in A]),
        (0.36, [mid(i, 0.84 * jit(0.04)) for i in range(n)]),
        (0.74, [(A[i][0] * 0.56 * jit(0.05), A[i][1] * 0.56 * jit(0.05)) for i in range(n)]),
        (0.93, [mid(i, 0.30 * jit(0.08)) for i in range(n)]),
    ]
    bm = bmesh.new()
    verts = []
    for lv, pts in rings:
        row = []
        for x, z in pts:
            row.append(bm.verts.new(c + Vector((x * w, lv * depth + 0.012 * lv * (x * x + z * z), z * h))))
        verts.append(row)
    top = bm.verts.new(c + Vector((0.0, depth, 0.0)))                  # 台面中心（九边扇形）
    back = bm.verts.new(c + Vector((0.0, -0.012, 0.0)))                # 背面中心

    tris = []                                                          # (v0, v1, v2, 环号)

    # A(对位) → B(错半格)：B[i] 在 A[i] 与 A[i+1] 之间
    for i in range(n):
        tris.append((verts[0][i], verts[0][(i + 1) % n], verts[1][i], 0))
        tris.append((verts[1][i], verts[1][(i - 1) % n], verts[0][i], 0.5))
    # B(错半格) → C(对位)：C[i] 在 B[i-1] 与 B[i] 之间
    for i in range(n):
        tris.append((verts[1][(i - 1) % n], verts[1][i], verts[2][i], 1))
        tris.append((verts[2][i], verts[2][(i + 1) % n], verts[1][i], 1.5))
    # C(对位) → D(错半格)
    for i in range(n):
        tris.append((verts[2][i], verts[2][(i + 1) % n], verts[3][i], 2))
        tris.append((verts[3][i], verts[3][(i - 1) % n], verts[2][i], 2.5))
    for i in range(n):                                                  # 平台面（D 环 → 中心）
        tris.append((verts[3][i], verts[3][(i + 1) % n], top, 3))
    for i in range(n):                                                  # 背面（A 环 → 背面中心）
        tris.append((verts[0][(i + 1) % n], verts[0][i], back, -1))
    ref = c + Vector((0, 0.45 * depth, 0))
    light = Vector((-0.45, 0.55, 0.70)).normalized()
    faces = []
    for a, b, d, ring in tris:
        try:
            f = bm.faces.new((a, b, d))
        except ValueError:
            continue
        f.normal_update()
        ctr = (a.co + b.co + d.co) / 3
        if f.normal.dot(ctr - ref) < 0:
            f.normal_flip()
        faces.append((f, ring))
    bm.normal_update()
    for f, ring in faces:
        lit = max(0.0, f.normal.dot(light))
        if ring < 0:
            f.material_index = 2                                        # 背面：深红
            continue
        base = {0: 0.20, 1: 0.42, 2: 0.62, 3: 0.92}[int(ring)]
        s = base + 0.45 * (lit - 0.45) + rnd.uniform(-0.07, 0.07)
        f.material_index = 0 if s > 0.80 else (1 if s > 0.46 else 2)
        f.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = False
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# ===== 圣心（第五轮） =====
def build_sacred_heart_r5(ctx, B, M, zc, small_gem):
    """胸前“终末圣心”（第五轮）：熔裂心板 → 刻面红宝石 → 金框（镶口）→ 荆棘藤；两侧金色羽翼环抱，金链垂饰。"""
    s = B.s
    T = ctx.title
    spec = rigid("Chest")
    sp2 = invdist(["Spine", "Chest"])
    g0 = 0.136
    c0 = B.on_torso(0, zc, g0)
    w1 = h1 = 0.355                                           # 心板半宽 / 半高
    sm = smooth_outline()
    # 心板：沿新轮廓的穹顶熔裂板（暗钢 + 少量余烬熔缝）
    ctx.part(outline_dome(f"{T} heart plate", c0, sm, w1, h1, 0.050, [M["molten"]]), spec)
    # 刻面红宝石：宝石半宽 / 半高略小于心板，台面凸起 0.14 m
    gw, gh = w1 * 0.76, h1 * 0.76
    ctx.part(ruby(f"{T} heart ruby", c0 + Vector((0, 0.030, 0.0)), gw, gh, 0.14,
                  [M["ruby_hot"], M["ruby_mid"], M["ruby_deep"]]), spec)
    # 金框：外框（镶口，四棱粗滚边）+ 内框细线（紧贴宝石腰圈）
    y_frame = c0.y + 0.020
    ctx.part(rim(f"{T} heart frame", outline_ring(c0, sm, w1, h1, y_frame, scale=1.04), 0.026, M["gilt"], closed=True), spec)
    ctx.part(rim(f"{T} heart frame inner", outline_ring(c0, sm, w1, h1, y_frame + 0.036, 0.012, scale=0.835), 0.012,
                 M["trim"], closed=True), spec)
    # 荆棘藤：自底尖起沿镶口外缘左右各一条攀升（取新轮廓上的点序），藤上长出尖刺
    n = len(sm)
    bot = min(range(n), key=lambda i: sm[i][1])
    for sd in (-1, 1):                                        # sd=+1：沿逆时针（向右上），sd=-1：顺时针（向左上）
        pts, rad = [], []
        m = 22
        reach = int(n * 0.47)
        for i in range(m):
            k = i / (m - 1)
            idx = bot + sd * int(round(lerp(0.0, reach, k)))
            x, z = sm[idx % n]
            kk = 1.20 + 0.055 * math.sin(i * 1.25)
            pts.append(Vector((c0.x + x * w1 * kk, y_frame + 0.012 + 0.016 * math.sin(i * 0.9), c0.z + z * h1 * kk)))
            rad.append(0.017 * (1.0 - 0.45 * k))
        ctx.part(tube(f"{T} heart vine {sd}", pts, rad, [M["gilt"]], n=4, per=1), spec)
        for i in range(2, m - 1, 3):
            p = pts[i]
            out = Vector((p.x - c0.x, 0, p.z - c0.z)).normalized()
            ctx.part(spike(f"{T} heart thorn {sd}{i}", p, p + (out * 0.9 + Vector((0, 0.45, 0))).normalized() * 0.085, 0.017,
                           [M["gilt"]], sides=3), spec)
    # 心尖（宝石底尖）下一枚金色泪滴坠
    bx, bz = sm[bot]
    ctx.part(small_gem(f"{T} heart drop", c0 + Vector((bx * w1 * 1.14, 0.045, bz * h1 * 1.14 - 0.02)), 0.032, M["gilt"],
                       (0.9, 0.8, 1.7)), spec)
    # 羽翼环抱：两侧各四片金羽，自宝石侧向外上扬（贴着胸甲表面；与第四轮相同）
    wing = ((60, 0.46, 0.20, 0.26), (40, 0.62, 0.22, 0.20), (20, 0.70, 0.23, 0.15), (0, 0.66, 0.22, 0.10))
    for sd in (-1, 1):
        for k, (deg, L, W, dz) in enumerate(wing):
            a = math.radians(deg)
            base = (w1 * 0.80 + 0.04 * k, zc + dz * h1 - 0.02 * k)
            torso_feather(ctx, B, f"{T} heart wing {sd}{k}", sd, base, a, L, W, M["gilded"], 0.118 - 0.010 * k, sp2,
                          ridge=0.018, nu=5, nv=7, rim_mat=M["trim"] if k < 3 else None, rim_r=0.009)
        chain_swag(ctx, B, f"{T} chain hi {sd}", sd, (0.74, zc + 0.46), (0.22, zc + 0.30), 0.22, 0.150, M["gilt"], sp2)
        chain_swag(ctx, B, f"{T} chain lo {sd}", sd, (0.80, zc + 0.10), (0.40, zc - 0.26), 0.16, 0.150, M["gilt"], sp2)
    return c0
