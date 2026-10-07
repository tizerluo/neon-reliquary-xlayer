"""Boss 7（灰烬炽天使）第四轮私有部件（只在 boss_7.py 里使用；不改 kit，缺的东西在这里新写）。

- 圣心核心：心形燃烧核心（熔裂心板 + 发光心形宝石 + 金框 + 荆棘藤）+ 金色羽翼环抱（贴着躯干表面的鎏金羽片）+ 金链垂饰。
- 层叠护喉：分片的尖底护喉甲片（三层错位，不再是一圈圈的环）。
- 铠甲手：分节手指（食 / 中 / 无名 / 小指各三节指甲片 + 指节金帽）、拇指、手背甲，握剑时手指包住剑柄。
- 护肘：圆顶护肘甲 + 上下两道关节罩，把肘部的紧身衣完全遮住。
"""

import math

import bmesh
from mathutils import Vector

from kit.core import (TAU, auto_smooth, finish, invdist, lerp, orient, rigid, smoothstep, spike, surface, tube)

from chars._b7_lib import blob, rim, sweep
from chars._b7r3_parts import plume_width, scale_uv


# ===== 心形 =====
def heart_xy(t):
    """心形轮廓（经典参数式，单位化到宽 ±1、高约 ±0.95，原点在中心）：t=0 为顶部凹口，t=π 为底尖，t∈(0,π) 在右侧。"""
    x = 16 * math.sin(t) ** 3
    y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
    return x / 16.0, (y + 2.5) / 15.0


def weld(obj, dist=1e-5):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def heart_dome(name, c, w, h, depth, mats, nu=36, nv=5, power=0.55, ref=None):
    """穹顶心形（面朝 +Y）：圆心 c，半宽 w、半高 h、穹高 depth；UV 取心形平面投影（熔裂贴图不被径向拉伸）。"""
    c = Vector(c)

    def P(u, v):
        x, z = heart_xy(u * TAU)
        d = depth * max(0.0, 1 - v ** 2.0) ** power
        return c + Vector((x * w * v, d, z * h * v))

    def uv(u, v):
        x, z = heart_xy(u * TAU)
        return (0.5 + 0.5 * x * v, 0.5 + 0.5 * z * v)
    obj = surface(name, P, nu, nv, mats, closed_u=True, uvfn=uv)
    weld(obj)
    orient(obj, lambda q: c - Vector((0, 0.5, 0)))
    return obj


def heart_outline(c, w, h, y, n=48, z0=0.0):
    c = Vector(c)
    pts = []
    for i in range(n):
        x, z = heart_xy(i / n * TAU)
        pts.append(Vector((c.x + x * w, y, c.z + z * h + z0)))
    return pts


# ===== 躯干上的贴面羽片 =====
def torso_feather(ctx, B, name, side, base, ang, L, W, mat, grow, spec, ridge=0.014, nu=5, nv=7, rim_mat=None,
                  rim_r=0.008, thick=0.012, uvs=(0.8, 1.0)):
    """贴着躯干表面的羽片（甲壳上的鎏金羽纹浮雕）：base=(x, z) 为右半侧起点（米），ang 为 x-z 平面内的方向角
    （0 朝外 +x、90° 朝上 +z），L 长、W 宽；轮廓取阔羽（根部窄柄、中段最宽、圆润收尖）；沿中脊略隆起。"""
    d = (math.cos(ang), math.sin(ang))
    pr = (-math.sin(ang), math.cos(ang))

    def pt(u, v):
        w = W * plume_width(v)
        x2 = base[0] + d[0] * v * L + pr[0] * (u - 0.5) * w
        z2 = base[1] + d[1] * v * L + pr[1] * (u - 0.5) * w
        return B.on_torso(side * x2, z2, grow + ridge * (1 - abs(2 * u - 1)) * math.sin(math.pi * min(1.0, v * 0.8 + 0.1)))
    obj = surface(name, lambda u, v: pt(u, v), nu, nv, [mat], uvfn=lambda u, v: (u * uvs[0], v * uvs[1]))
    orient(obj, lambda c: Vector((0, 0, c.z)))
    ctx.part(finish(obj, thick, 0, 0), spec)
    if rim_mat is not None:
        edge = [pt(0.0, j / 3 * 0.9) for j in range(1, 4)] + [pt(0.5, 1.0)] + [pt(1.0, (3 - j) / 3 * 0.9) for j in range(0, 3)]
        edge = [Vector(p) + (Vector(p) - Vector((0, p.y - 0.3, p.z))).normalized() * 0.006 for p in edge]
        ctx.part(rim(f"{name} rim", edge, rim_r, rim_mat), spec)
    return pt


def chain_swag(ctx, B, name, side, pa, pb, sag, grow, mat, spec, links=13, r=(0.028, 0.016)):
    """贴着躯干垂下的金链：自 pa=(x, z) 到 pb=(x, z) 的悬链线（下垂 sag 米），粗细相间的半径让细管读成一节节链环。"""
    pts, rad = [], []
    for i in range(links):
        t = i / (links - 1)
        x = lerp(pa[0], pb[0], t)
        z = lerp(pa[1], pb[1], t) - sag * 4 * t * (1 - t)
        pts.append(B.on_torso(side * x, z, grow))
        rad.append(r[0] if i % 2 == 0 else r[1])
    ctx.part(tube(name, pts, rad, [mat], n=4, per=1), spec)
    return pts


# ===== 圣心贴图 =====
def heart_maps(size=256):
    """心形宝石的发光贴图（UV 为心形平面投影，圆心 0.5, 0.5）：圆心金白 → 橙 → 边缘暗红的径向渐变 + 淡淡的放射脉络，
    比纯色自发光更有纵深，也不会被 AgX 压成一块发白的桃色。返回 (base, emission, None)。"""
    import numpy as np
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    dx, dy = (u - 0.5) * 2, (v - 0.5) * 2
    d = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)
    vein = (0.5 + 0.5 * np.cos(ang * 9 + d * 4.0)) ** 3 * np.clip(d * 1.6, 0, 1)
    t = np.clip(d / 0.95, 0, 1)
    hot, mid, edge = (np.array(c, np.float32)[None, None, :] for c in ((1.0, 0.74, 0.46), (1.0, 0.40, 0.13), (0.80, 0.13, 0.04)))
    k1 = np.clip(t * 2, 0, 1)[..., None]
    k2 = np.clip(t * 2 - 1, 0, 1)[..., None]
    em = (hot * (1 - k1) + mid * k1) * (1 - k2) + edge * k2
    em = em * (0.78 + 0.22 * vein[..., None])
    base = np.stack([0.30 + 0 * d, 0.06 + 0 * d, 0.025 + 0 * d], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), None


# ===== 圣心核心 =====
def build_sacred_heart(ctx, B, M, zc, small_gem):
    """胸前“终末圣心”：熔裂心板（暗钢 + 余烬裂纹）→ 心形发光宝石 → 金框 → 荆棘藤；两侧金色羽翼环抱，金链垂饰。
    返回心形中心点（供外部参考）。"""
    s = B.s
    T = ctx.title
    spec = rigid("Chest")
    sp2 = invdist(["Spine", "Chest"])
    g0 = 0.136 * 1.0                                       # 心板底面离躯干的外扩量（鎏金胸板表面在 ~0.13）
    c0 = B.on_torso(0, zc, g0)
    w1 = h1 = 0.355                                         # 心板半宽 / 半高
    ctx.part(heart_dome(f"{T} heart plate", c0, w1, h1, 0.050, [M["molten"]]), spec)
    # 发光心形宝石（凸起、半径略小于心板）
    ctx.part(heart_dome(f"{T} heart gem core", c0 + Vector((0, 0.030, 0.012)), w1 * 0.74, h1 * 0.74, 0.125,
                        [M["heart"]], nu=32, nv=5, power=0.62), spec)
    # 金框：外框（四棱粗滚边）+ 内框细线
    y_frame = c0.y + 0.020
    ctx.part(rim(f"{T} heart frame", heart_outline(c0, w1 * 1.04, h1 * 1.04, y_frame, 56), 0.026, M["gilt"], closed=True),
             spec)
    ctx.part(rim(f"{T} heart frame inner", heart_outline(c0, w1 * 0.80, h1 * 0.80, y_frame + 0.036, 40, 0.012), 0.012,
                 M["trim"], closed=True), spec)
    # 荆棘藤：自底尖起沿心形外缘左右各一条攀升，藤上长出尖刺
    for sd in (-1, 1):
        pts, rad = [], []
        n = 22
        for i in range(n):
            t = lerp(math.pi - 0.10, 0.45, i / (n - 1))
            x, z = heart_xy(t)
            k = 1.20 + 0.055 * math.sin(i * 1.25)
            pts.append(Vector((c0.x + sd * x * w1 * k, y_frame + 0.012 + 0.016 * math.sin(i * 0.9), c0.z + z * h1 * k)))
            rad.append(0.017 * (1.0 - 0.45 * i / (n - 1)))
        ctx.part(tube(f"{T} heart vine {sd}", pts, rad, [M["gilt"]], n=4, per=1), spec)
        for i in range(2, n - 1, 3):
            p = pts[i]
            out = Vector((p.x - c0.x, 0, p.z - c0.z)).normalized()
            ctx.part(spike(f"{T} heart thorn {sd}{i}", p, p + (out * 0.9 + Vector((0, 0.45, 0))).normalized() * 0.085, 0.017,
                           [M["gilt"]], sides=3), spec)
    # 心尖下一枚金色泪滴坠 + 顶部一点余烬
    ctx.part(small_gem(f"{T} heart drop", c0 + Vector((0, 0.045, -h1 * 1.12)), 0.032, M["gilt"], (0.9, 0.8, 1.7)), spec)
    # 羽翼环抱：心的两侧各四片金羽，自心侧向外上扬（贴着胸甲表面）
    wing = ((60, 0.46, 0.20, 0.26), (40, 0.62, 0.22, 0.20), (20, 0.70, 0.23, 0.15), (0, 0.66, 0.22, 0.10))
    for sd in (-1, 1):
        for k, (deg, L, W, dz) in enumerate(wing):
            a = math.radians(deg)
            base = (w1 * 0.80 + 0.04 * k, zc + dz * h1 - 0.02 * k)
            torso_feather(ctx, B, f"{T} heart wing {sd}{k}", sd, base, a, L, W, M["gilded"], 0.118 - 0.010 * k, sp2,
                          ridge=0.018, nu=5, nv=7, rim_mat=M["trim"] if k < 3 else None, rim_r=0.009)
        # 金链：自锁骨外侧挂到心形上缘，再一道更低的挂到心侧
        chain_swag(ctx, B, f"{T} chain hi {sd}", sd, (0.74, zc + 0.46), (0.22, zc + 0.30), 0.22, 0.150, M["gilt"], sp2)
        chain_swag(ctx, B, f"{T} chain lo {sd}", sd, (0.80, zc + 0.10), (0.40, zc - 0.26), 0.16, 0.150, M["gilt"], sp2)
    return c0


# ===== 层叠护喉 =====
def gorget_plates(ctx, B, M, tiers):
    """分片尖底护喉甲片：tiers 为 [(z0, z1, r0, r1, 片数, 起始相位, 角度范围(弧度, 以正前方为中心), 尖长系数)]，
    逐层向下放大、错位半片相压，每片暗钢 + 下缘金边；取代一圈圈的颈环（远看像弹簧）。"""
    s = B.s
    T = ctx.title
    spec = invdist(["Chest", "Neck"])
    for k, (z0, z1, r0, r1, n, phase, span, tip) in enumerate(tiers):
        zt, zb = B.z(z0), B.z(z1)
        da = span / n
        for j in range(n):
            ac = -span / 2 + (j + 0.5 + phase) * da
            if abs(ac) > span / 2 + 1e-6:
                continue

            def P(x, y, ac=ac, da=da, zt=zt, zb=zb, r0=r0, r1=r1, tip=tip):
                a = ac + (x - 0.5) * da * 1.22
                z = lerp(zt, zb, y) - tip * s * (1 - abs(2 * x - 1)) ** 1.3 * y ** 1.2
                r = lerp(r0, r1, y) * s * (1 + 0.04 * (1 - abs(2 * x - 1)))
                return Vector((r * math.sin(a), 0.004 * s + 0.006 * s + r * math.cos(a) * 0.92, z))
            plate = surface(f"{T} gorget plate {k}{j}", lambda u, v, P=P: P(u, v), 5, 4, [M["steel"]],
                            uvfn=lambda u, v: (u * 0.5, v * 0.3))
            orient(plate, lambda c: Vector((0, 0.01 * s, c.z)))
            ctx.part(finish(plate, 0.0055 * s, 1, 0), spec)
            edge = [P(0.0, 0.62)] + [P(0.0, 1.0)] + [P(0.5, 1.0)] + [P(1.0, 1.0)] + [P(1.0, 0.62)]
            edge = [p + Vector((p.x, p.y - 0.01 * s, 0)).normalized() * 0.010 for p in edge]
            ctx.part(rim(f"{T} gorget plate rim {k}{j}", edge, 0.0036 * s, M["trim"]), spec)


# ===== 铠甲手（分节手指，握拢剑柄） =====
def finger_arc(C, f, n, sv, off, ro, a0, a1, m=3):
    """围绕剑柄轴（过 C、方向 sv）的一段圆弧：角度 ph 自 +f 向 +n 增大；off 为沿剑柄轴的偏移。"""
    pts = []
    for i in range(m):
        ph = math.radians(lerp(a0, a1, i / (m - 1)))
        pts.append(C + (f * math.cos(ph) + n * math.sin(ph)) * ro + sv * off)
    return pts


def gauntlet_r4(ctx, B, side, label, M, HS, GRIP_A, GRIP_B, small_gem):
    """握剑的铠甲手：手背甲 + 四指（各三节指甲片、指节金帽）+ 拇指，指节绕剑柄成圈、指尖收向掌心。
    坐标系同第三轮：腕 → 握点 C = 腕 + f·A + n·B；握点处的剑柄轴 = 拇指方向 sv。"""
    s = B.s * HS
    T = ctx.title
    a = B.arms[label]
    wrist, elbow = a["wrist"], a["elbow"]
    f = ((wrist - elbow).normalized() + Vector((0, 0, -0.55))).normalized()
    n = Vector((0, 1, 0.15))
    n = (n - f * n.dot(f)).normalized()
    s0 = f.cross(n).normalized()
    sv = -s0 if s0.x * side < 0 else s0
    knuckle = wrist + f * 0.095 * s
    C = wrist + f * GRIP_A * s + n * GRIP_B * s
    spec = rigid(f"Hand.{label}")

    def at(ph_deg, r, off=0.0):
        ph = math.radians(ph_deg)
        return C + (f * math.cos(ph) + n * math.sin(ph)) * r + sv * off

    # 手背甲：自腕口到掌指关节的拱形暗钢甲（宽 ~0.38 m，中脊鎏金，嵌熔裂宝石）——侧视 / 俯视时一眼是“手背”
    def back(u, v):
        base = wrist + f * (0.012 + 0.108 * v) * s
        wdt = (0.150 + 0.050 * v) * s * 0.74
        arch = 0.060 * s * (1 - u * u) ** 0.7 * (0.55 + 0.45 * math.sin(math.pi * min(1.0, v * 0.9 + 0.1)))
        return base + sv * (u * wdt) - n * (arch + 0.040 * s)
    plate = surface(f"{T} hand back {label}", lambda uu, vv: back(2 * uu - 1, vv), 9, 6, [M["steel"]],
                    uvfn=lambda uu, vv: (uu * 0.7, vv * 0.6))
    orient(plate, lambda c: wrist + f * 0.05 * s + n * 0.05 * s)
    ctx.part(finish(plate, 0.012 * s * 0.5, 0, 0), spec)
    for q in (-1.0, 1.0):
        edge = [back(q, j / 5) + (back(q, j / 5) - back(0, j / 5)).normalized() * 0.006 for j in range(6)]
        ctx.part(rim(f"{T} hand back edge {label}{q}", edge, 0.0075, M["trim"]), spec)
    ridge = [back(0, j / 5) - n * 0.012 for j in range(6)]
    ctx.part(tube(f"{T} hand back ridge {label}", ridge, [0.020, 0.024, 0.026, 0.026, 0.024, 0.020], [M["gilt"]], n=6,
                  per=1), spec)
    ctx.part(blob(f"{T} hand plate {label}", back(0, 0.50) - n * 0.040, (0.032 * s, 0.040 * s, 0.008 * s),
                  [M["molten"]], 12, 6, axes=(sv, f, n)), spec)
    ctx.part(small_gem(f"{T} hand gem {label}", back(0, 0.50) - n * 0.070, 0.011 * s, M["glow2"], (1.0, 1.0, 1.0)), spec)
    # 四指：沿剑柄轴并排（拇指侧 → 小指侧），每指三节、各节拱起的暗钢甲片（嵌金卷草）排成整齐的“甲片方阵”——
    # 节缝沿剑柄轴方向纵向贯通（金色护指杠 / 关节条），一眼是铠甲手而不是一圈圈的环；指尖带内扣的尖爪，掌指关节处金刺。
    # 拳的半径取 0.15 m（剑柄半径 0.08 m），与粗大的护臂配套：巨人的手要有分量，而不是细细一束指环。
    ro = 0.150
    sizes = (1.00, 1.06, 0.98, 0.84)
    wids = [0.0455 * k for k in sizes]
    offs, x = [], 0.1865
    for w in wids:
        offs.append(x - w)
        x -= 2 * w + 0.006
    cols = ((-38, 28), (36, 92), (98, 152))
    # 衬里：整圈暗色圆柱衬（甲片间的缝里看到的是衬里，两端收口）
    def liner(u, v):
        return at(u * 360.0, ro - 0.016, lerp(offs[0] + wids[0], offs[-1] - wids[-1], v))
    lin = surface(f"{T} fist liner {label}", liner, 20, 2, [M["slate"]], closed_u=True)
    orient(lin, lambda c: C + sv * (c - C).dot(sv))
    ctx.part(finish(lin, 0.012, 0, 0), spec)
    for i, (o, rw) in enumerate(zip(offs, wids)):
        for j, (a0, a1) in enumerate(cols):
            if i == 3 and j == 2:
                a1 -= 14                                   # 小指短一截
            bump = 0.011 * (1.0 - 0.08 * j)

            def tile(u, v, o=o, rw=rw, a0=a0, a1=a1, bump=bump):
                ph = lerp(a0 + 1.5, a1 - 1.5, v)
                r = ro + bump * math.sin(math.pi * u) ** 0.7 * math.sin(math.pi * v) ** 0.55
                return at(ph, r, o + rw * (2 * u - 1) * 0.95)
            pl = surface(f"{T} finger plate {label}{i}{j}", tile, 5, 5, [M["steel"]],
                         uvfn=lambda u, v, i=i, j=j: (0.2 * u + 0.23 * i, 0.2 * v + 0.31 * j))
            orient(pl, lambda c: C + sv * (c - C).dot(sv))
            ctx.part(finish(pl, 0.014, 0, 0), spec)
        a_end = cols[2][1] - (14 if i == 3 else 0)
        tip = at(a_end, ro + 0.010, o)
        tdir = (-f * math.sin(math.radians(a_end)) + n * math.cos(math.radians(a_end))) * 0.9 - \
            (f * math.cos(math.radians(a_end)) + n * math.sin(math.radians(a_end))) * 0.5
        ctx.part(spike(f"{T} fingertip {label}{i}", tip, tip + tdir.normalized() * 0.065, rw * 0.62, [M["gilt"]], sides=4),
                 spec)
    # 纵向节缝金条：掌指护指杠（粗）+ 近节 / 中节 / 指尖三道细条，贴在甲片缝上，沿剑柄轴贯穿四指
    for k, (ang, dr, rad) in enumerate(((-44, 0.034, 0.026), (32, 0.026, 0.0105), (95, 0.026, 0.0105), (155, 0.020, 0.0090))):
        bar = [at(ang, ro + dr, q) for q in (offs[0] + wids[0] * 0.95, offs[1], offs[2], offs[3] - wids[3] * 0.95)]
        ctx.part(tube(f"{T} fist seam {label}{k}", bar, [rad] * 4, [M["gilt"]], n=4 if k else 6, per=2), spec)
    out = (f * math.cos(math.radians(-44)) + n * math.sin(math.radians(-44)))
    for i, rw in enumerate(wids):
        kp = at(-44, ro + 0.050, offs[i])
        ctx.part(spike(f"{T} knuckle spike {label}{i}", kp, kp + (out * 0.8 + f * 0.6).normalized() * 0.125 * sizes[i],
                       0.0155 * sizes[i], [M["gilt"]], sides=4), spec)
    # 拇指：双手握剑时拇指顺着剑柄轴向剑尖方向压在食指、中指的甲片上（不绕圈）——一根粗壮的圆甲（嵌金卷草贴图的扫掠管），
    # 指根一枚金色关节帽，指尖一枚指甲爪；略微拱起并向外偏斜。
    pth = 108
    th = [at(pth + 8, ro + 0.060, 0.010), at(pth, ro + 0.074, 0.052), at(pth - 5, ro + 0.078, 0.102),
          at(pth - 12, ro + 0.070, 0.148), at(pth - 20, ro + 0.050, 0.176)]
    ctx.part(sweep(f"{T} thumb {label}", th, [0.052, 0.058, 0.056, 0.050, 0.036], [M["steel"]], n=10, per=3, tile=0.34), spec)
    ctx.part(blob(f"{T} thumb joint {label}", th[1].lerp(th[2], 0.45) + (th[1] - C).normalized() * 0.050,
                  (0.034, 0.034, 0.034), [M["gilt"]], 8, 5), spec)
    ctx.part(spike(f"{T} thumb claw {label}", th[-1], th[-1] + (sv * 0.9 + (th[-1] - C).normalized() * 0.2).normalized() * 0.045,
                   0.030, [M["gilt"]], sides=4), spec)
    B.hands[label] = {"wrist": wrist, "knuckle": knuckle, "f": f, "n": n, "s": sv, "fingers": {}, "grip": C}


# ===== 护肘 =====
def couter_r4(ctx, B, M, side, label, small_gem, ridge_blade):
    """圆顶护肘甲 + 上 / 下两道关节罩：整个肘部（含紧身衣露出的肘窝）都被甲遮住，不留弹簧状的圈。"""
    s = B.s
    T = ctx.title
    a = B.arms[label]
    E = a["elbow"]
    up_axis = (a["elbow"] - a["shoulder"]).normalized()
    fd = (a["wrist"] - a["elbow"]).normalized()
    blend = rigid((f"UpperArm.{label}", 0.5), (f"Forearm.{label}", 0.5))
    c = E + Vector((side * 0.05, -0.10, -0.02))
    ctx.part(blob(f"{T} couter {label}", c, (0.31, 0.33, 0.34), [M["steel"]], 18, 10, tile=1.0), blend)
    # 护肘金环（围着圆顶的赤道，法向沿外侧）
    ax = Vector((side, 0.0, 0.0))
    u2 = Vector((0, 1, 0))
    v2 = ax.cross(u2)
    ring = [c + ax * 0.10 + (u2 * math.cos(t) + v2 * math.sin(t)) * 0.33 for t in [i / 20 * TAU for i in range(20)]]
    ctx.part(rim(f"{T} couter ring {label}", ring, 0.017, M["gilt"], closed=True), blend)
    ctx.part(small_gem(f"{T} couter gem {label}", c + ax * 0.30 + Vector((0, -0.06, 0)), 0.060, M["glow2"], (1, 1, 1)),
             blend)
    # 上 / 下关节罩：与上臂 / 前臂同轴的喇叭口甲环，跨过肘窝相互叠压（每片挂各自的骨）
    for tag, bone, axis, z0, z1, ra, rb in (("up", f"UpperArm.{label}", up_axis, -0.36, -0.10, 0.380, 0.335),
                                            ("lo", f"Forearm.{label}", fd, 0.02, 0.30, 0.345, 0.38)):
        p0, p1 = E + axis * z0, E + axis * z1
        x = axis.orthogonal().normalized()
        y = axis.cross(x)
        da = (p1 - p0).normalized()

        def cone(u, v, p0=p0, p1=p1, x=x, y=y, ra=ra, rb=rb):
            th = u * TAU
            return p0.lerp(p1, v) + (x * math.cos(th) + y * math.sin(th)) * lerp(ra, rb, v)

        def on_axis(q, p0=p0, da=da):
            return p0 + da * (q - p0).dot(da)
        band = surface(f"{T} couter lame {tag} {label}", cone, 20, 3, [M["steel"]], closed_u=True,
                       uvfn=lambda u, v: (u * 2.0, v * 0.4))
        orient(band, on_axis)
        ctx.part(finish(band, 0.016, 1, 0), rigid(bone))
        v = 1.0 if tag == "up" else 0.0
        edge = [cone(i / 20, v) for i in range(20)]
        edge = [q + (q - on_axis(q)).normalized() * 0.014 for q in edge]
        ctx.part(rim(f"{T} couter lame rim {tag} {label}", edge, 0.011, M["trim"], closed=True), rigid(bone))
    # 肘后三叠金刃：向后外侧扇开
    for k, (dv, L, W, mat) in enumerate(((Vector((side * 0.65, -0.70, 0.30)), 0.78, 0.17, "gilt"),
                                         (Vector((side * 0.95, -0.25, 0.05)), 0.62, 0.15, "steel"),
                                         (Vector((side * 0.60, -0.75, -0.45)), 0.50, 0.13, "gilt"))):
        d = dv.normalized()
        ya = Vector((0, 0, 1)) - d * d.z
        ya.normalize()
        ctx.part(ridge_blade(f"{T} couter blade {label}{k}", L * s / 3.0, W * s / 3.0, 0.018 * s, [M[mat]],
                             c + Vector((side * 0.10, -0.12, 0.0)), d, ya, n=7, sweep=0.10), blend)
