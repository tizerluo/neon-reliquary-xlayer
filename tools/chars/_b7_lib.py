"""灰烬炽天使（boss-7）私有工具：带中脊的刃片网格、带 UV 的扫掠管、UV 椭球、火舌、余烬贴图、
带缩放通道的动作写入、参数轨道、姿态混合、穿插自检与面数统计。

只被 tools/chars/boss_7.py 引用；不改动 tools/kit/，kit 里不够用的函数在这里复制后改写（见各函数注释）。
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from kit.core import (TAU, auto_smooth, bm_object, box_blur, circuit_maps, clamp, height_normal, lerp, smoothstep,
                      surface, tube, voronoi)
from kit.rig import I3


# ===== 网格 =====
def feather_width(t, root=0.36, belly=0.26, tip=1.35):
    """刃羽宽度系数：根部窄柄 → belly 处最宽 → 尖端收尖（t 为 0..1 的长度比例）。"""
    if t <= belly:
        return root + (1 - root) * math.sin(math.pi / 2 * t / belly)
    return max(0.0, 1 - ((t - belly) / (1 - belly)) ** tip)


def ridge_blade(name, L, W, depth, mats, origin, xaxis, yaxis, width=None, edge=0.24, n=10, bend=0.0, sweep=0.0,
                notch=0.0, smooth_angle=6.0, lite=False):
    """带中脊的刃片 / 刃羽：沿 xaxis 长 L、沿 yaxis 宽 W（width(t)∈[0,1] 为宽度系数），截面为菱形——
    中脊厚 depth、刃口厚 edge*depth；bend 让刃身沿法向拱起（占长度比例），sweep 让刃尖向 +yaxis 弯（前缘弧），
    notch 为根部 V 形缺口深度（占长度比例）。
    kit.core.plate 只有轮廓顶点、面内无法起脊（凸起只能靠三角化扇面），这里自建条带网格，
    UV：u 沿长度 0→1、v 沿宽度 0→1（中脊在 v=0.5）。"""
    o, xa = Vector(origin), Vector(xaxis).normalized()
    ya = Vector(yaxis)
    ya = (ya - xa * ya.dot(xa)).normalized()
    na = xa.cross(ya).normalized()
    wf = width or feather_width
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    uv = []

    def vert(x, y, z, u, v):
        bv = bm.verts.new(o + xa * x + ya * y + na * z)
        uv.append((u, v))
        return bv
    if lite:
        # 精简版：刃口前后共用顶点（刃口厚度为 0），每段只有四个面（普通版六个），羽片这种数量大的件省三分之一面
        rows = []
        for k in range(n):
            t = k / n
            hw = 0.5 * W * max(wf(t), 0.02)
            taper = min(1.0, wf(t) / 0.22) ** 0.7
            cy = sweep * L * t * t
            cz = bend * L * math.sin(math.pi * t)
            hc = 0.5 * depth * taper
            xc = t * L + (notch * L if k == 0 else 0.0)
            rows.append((vert(t * L, cy - hw, cz, t, 0.0), vert(xc, cy, cz + hc, t, 0.5), vert(t * L, cy + hw, cz, t, 1.0),
                         vert(xc, cy, cz - hc, t, 0.5)))
        tip = vert(L, sweep * L, 0.0, 1.0, 0.5)
        faces = []
        for k in range(n - 1):
            l0, f0, r0, b0 = rows[k]
            l1, f1, r1, b1 = rows[k + 1]
            faces += [(l0, f0, f1, l1), (f0, r0, r1, f1), (b0, l0, l1, b1), (r0, b0, b1, r1)]
        l0, f0, r0, b0 = rows[-1]
        faces += [(l0, f0, tip), (f0, r0, tip), (b0, l0, tip), (r0, b0, tip)]
        l0, f0, r0, b0 = rows[0]
        faces.append((l0, b0, r0, f0))
        bm.verts.index_update()
        for f in faces:
            face = bm.faces.new(f)
            for loop in face.loops:
                loop[uvl].uv = uv[loop.vert.index]
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        obj = bm_object(name, bm, mats, smooth=True)
        return auto_smooth(obj, smooth_angle)
    rows = []
    for k in range(n):
        t = k / n
        hw = 0.5 * W * max(wf(t), 0.02)
        taper = min(1.0, wf(t) / 0.22) ** 0.7
        cy = sweep * L * t * t
        cz = bend * L * math.sin(math.pi * t)
        hc, he = 0.5 * depth * taper, 0.5 * depth * edge * taper
        xc = t * L + (notch * L if k == 0 else 0.0)
        row = []
        for s in (1, -1):
            row.append((vert(t * L, cy - hw, cz + s * he, t, 0.0), vert(xc, cy, cz + s * hc, t, 0.5),
                        vert(t * L, cy + hw, cz + s * he, t, 1.0)))
        rows.append(row)
    tip = vert(L, sweep * L, 0.0, 1.0, 0.5)
    faces = []
    for k in range(n - 1):
        (fl, fc, fr), (bl, bc, br) = rows[k]
        (fl2, fc2, fr2), (bl2, bc2, br2) = rows[k + 1]
        faces += [(fl, fc, fc2, fl2), (fc, fr, fr2, fc2), (bc, bl, bl2, bc2), (br, bc, bc2, br2),
                  (bl, fl, fl2, bl2), (fr, br, br2, fr2)]
    (fl, fc, fr), (bl, bc, br) = rows[-1]
    faces += [(fl, fc, tip), (fc, fr, tip), (bc, bl, tip), (br, bc, tip), (bl, fl, tip), (fr, br, tip)]
    (fl, fc, fr), (bl, bc, br) = rows[0]
    faces.append((fl, bl, bc, br, fr, fc))
    bm.verts.index_update()
    for f in faces:
        face = bm.faces.new(f)
        for loop in face.loops:
            loop[uvl].uv = uv[loop.vert.index]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = bm_object(name, bm, mats, smooth=True)
    return auto_smooth(obj, smooth_angle)


def sweep(name, points, radii, mats, n=12, per=3, tile=1.0, closed=False, cap=True):
    """带 UV 的扫掠管（改自 nyx_lib.tube：原版不写 UV，贴图材质会整段取到贴图左下角一个像素）。
    u 绕管一周、v 按弧长 / tile 平铺。"""
    from kit.core import catmull
    pts, rad = catmull(points, radii, per) if per > 1 else ([Vector(p) for p in points], list(radii))
    m = len(pts)
    tang = []
    for i in range(m):
        d = pts[(i + 1) % m] - pts[i - 1] if closed else pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]
        tang.append(d.normalized())
    n0 = Vector((0, 0, 1)) - tang[0] * tang[0].z
    if n0.length < 1e-5:
        n0 = Vector((1, 0, 0)) - tang[0] * tang[0].x
    nrm = [n0.normalized()]
    for i in range(1, m):
        v = nrm[-1] - tang[i] * nrm[-1].dot(tang[i])
        nrm.append(v.normalized() if v.length > 1e-6 else nrm[-1])
    acc = [0.0]
    for i in range(1, m):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    circ = TAU * max(rad) if max(rad) > 0 else 1.0
    ru = max(1, round(circ / tile))
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for i in range(m):
        b = tang[i].cross(nrm[i])
        rings.append([bm.verts.new(pts[i] + (nrm[i] * math.cos(TAU * k / n) + b * math.sin(TAU * k / n)) * rad[i])
                      for k in range(n)])
    segs = m if closed else m - 1
    for i in range(segs):
        i2 = (i + 1) % m
        for k in range(n):
            k2 = (k + 1) % n
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i2][k2], rings[i2][k]))
            for loop, (kk, ii) in zip(f.loops, ((k, i), (k + 1, i), (k + 1, i2), (k, i2))):
                vv = acc[ii] if not (closed and ii == 0 and i == m - 1) else acc[-1] + (pts[0] - pts[-1]).length
                loop[uvl].uv = (kk / n * ru, vv / tile)
    if cap and not closed:
        for ring in (rings[0], rings[-1]):
            try:
                bm.faces.new(ring)
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats)


def blob(name, center, radii, mats, nu=24, nv=14, tile=None, axes=None):
    """带 UV 的椭球（nyx_lib.ellipsoid 用 create_uvsphere 且不生成 UV，贴图材质会失效）；
    axes=(ax, ay, az) 时按给定三轴摆放（手背甲这类斜放的椭球）。"""
    c = Vector(center)
    ax, ay, az = [Vector(a) for a in (axes or ((1, 0, 0), (0, 1, 0), (0, 0, 1)))]

    def fn(u, v):
        a, b = u * TAU, v * math.pi
        return c + ax * (math.sin(a) * math.sin(b) * radii[0]) + ay * (math.cos(a) * math.sin(b) * radii[1]) + \
            az * (math.cos(b) * radii[2])
    uvfn = None
    if tile:
        ru = max(1, round(TAU * max(radii[0], radii[1]) / tile))
        uvfn = lambda u, v: (u * ru, (1 - v) * math.pi * radii[2] / tile)   # noqa: E731
    obj = surface(name, fn, nu, nv, mats, closed_u=True, uvfn=uvfn)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def flame(name, base, direction, height, radius, mats, lobes=5, twist=2.2, nu=14, nv=9, seed=0.0, amp=0.62,
          curl=0.20):
    """火舌：沿 direction 伸出、扭转的花瓣锥（改自 _bossA_common.flame：花瓣起伏更深、尖端更细并向一侧卷，
    远看才像火焰而不是光滑锥体；默认分段更省面）。"""
    b = Vector(base)
    d = Vector(direction).normalized()
    side = d.orthogonal().normalized()
    other = d.cross(side)

    def fn(u, v):
        a = u * TAU
        body = (1 - v) ** 1.25 * (0.55 + 0.45 * math.sin(math.pi * min(1.0, v * 1.8 + 0.30)))
        petal = 1 + amp * math.sin(lobes * a + twist * v * TAU + seed) * smoothstep(0.05, 0.5, v)
        r = radius * body * petal
        wob = curl * height * v ** 1.6 * math.sin(seed * 1.7 + v * 4.0)
        return b + d * (height * v) + side * (math.cos(a) * r + wob) + other * (math.sin(a) * r)
    return surface(name, fn, nu, nv, mats, closed_u=True)


def pauldron_lite(ctx, B, side, label, mat, lames=3, radius=0.11, spread=1.32, rise=1.18, tilt=0.30, spire=0.0,
                  spire_at=-0.30, spire_dir=(0.28, -0.22, 1.0), theta=((0.08, 0.92), (0.70, 1.30), (1.10, 1.66)),
                  shrink=(1.0, 0.955, 0.90), thick=0.007, spec=None, ridge=0.0, nu=36, nv=9):
    """分层肩甲（复制自 kit.humanoid.pauldron）：kit 版每片固定细分一级（五片巨型肩甲单侧 2 万面），
    这里不细分、改用 nu×nv 直接取点；不带滚边与宝石（配方里用四棱滚边自己加）。"""
    from kit.core import finish as _finish, orient as _orient
    from mathutils import Matrix
    s = B.s
    shoulder = B.arms[label]["shoulder"] + Vector((0, 0.001, 0.02 * s))

    def lp(k, u, t):
        th0, th1 = theta[k]
        rr = radius * s * shrink[k]
        phi = u * spread
        taper = 1 - abs(u) ** 2.6
        mid, half = (th0 + th1) / 2, (th1 - th0) / 2
        th = mid + (t - 0.5) * 2 * half * taper
        d = Vector((math.cos(phi) * math.sin(th) * side, math.sin(phi) * math.sin(th) * rise, math.cos(th)))
        p = shoulder + d * rr * (1 + 0.06 * (1 - abs(u)) + ridge * math.exp(-(u / 0.12) ** 2))
        if k == 0 and spire:
            sp = spire * s * math.exp(-((u - spire_at) / 0.20) ** 2) * (1 - t) ** 2.0
            p += Vector((side * spire_dir[0], spire_dir[1], spire_dir[2])).normalized() * sp
        return shoulder + Matrix.Rotation(side * tilt, 3, "Y") @ (p - shoulder)
    for k in range(lames):
        lame = surface(f"{ctx.title} pauldron {label}{k}", lambda u, v, k=k: lp(k, 2 * u - 1, v), nu, nv, [mat])
        _orient(lame, lambda c: shoulder)
        ctx.part(_finish(lame, thick, 0, 0), spec)
    return lp, shoulder


def rim(name, points, radius, mat, closed=False):
    """省面的滚边：四棱细管（kit.trim 为六棱；Boss 的滚边多、游戏版不减面，六棱太贵）。"""
    return tube(name, points, [radius] * len(points), [mat], n=3, closed=closed, per=1)


def ring_around(a, b, t, r, n=24):
    """绕线段 a→b 第 t 处的一圈点（肢体上的金箍）。"""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    x = d.orthogonal().normalized()
    z = d.cross(x)
    c = a.lerp(b, t)
    return [c + (x * math.cos(TAU * i / n) + z * math.sin(TAU * i / n)) * r for i in range(n)]


# ===== 程序化贴图（第 0 行为图像底边，与 kit.core 一致） =====
def ember_crack_maps(emit_rgb, base_rgb=(0.19, 0.18, 0.175), size=1024, seed=7, cells=7, width=0.032, fine=0.10,
                     heat=1.0, ash=0.35, soot=0.0, keep=1.0):
    """余烬接缝甲面（改写 kit.core.crack_maps：原版细裂纹也按 0.45 发光，满身红纹太亮）：
    主裂纹发光、细裂纹只压暗不发光（fine 控制残余发光），块面带灰烬颗粒与明暗；soot 让接缝两侧熏黑，
    keep<1 时只保留一部分主裂纹发光（其余只是暗缝），避免满身熔岩网。"""
    rng = np.random.default_rng(seed)
    f1, f2, idx = voronoi(size, cells, rng)
    crack = np.clip(1 - (f2 - f1) / width, 0, 1) ** 2
    g1, g2, _ = voronoi(size, cells * 3, rng)
    finec = np.clip(1 - (g2 - g1) / (width * 0.45), 0, 1) ** 3
    if keep < 1.0:
        lit = (box_blur(rng.random((size, size)).astype(np.float32), 40) - 0.5) * 14 + (keep - 0.5) * 3
        lit = np.clip(lit, 0, 1)
    else:
        lit = np.ones((size, size), np.float32)
    hot = crack * lit
    ember = box_blur(hot, 6)
    em = np.stack([np.clip(hot + ember * 0.35 + finec * fine, 0, 1) * c * heat for c in emit_rgb], axis=2)
    cellv = (np.sin(idx * 1.7 + seed) * 0.5 + 0.5)[..., None]
    grain = (box_blur(rng.random((size, size)).astype(np.float32), 2) - 0.5)[..., None]
    cloud = (box_blur(rng.random((size, size)).astype(np.float32), 28) - 0.5)[..., None]
    tone = 0.78 + 0.34 * cellv + grain * ash + cloud * 2.2
    base = np.array(base_rgb)[None, None, :] * tone
    base = base * (1 - 0.55 * finec[..., None]) * (1 - 0.6 * crack[..., None])
    if soot:
        base = base * (1 - soot * np.clip(box_blur(crack, 10) * 3.0, 0, 1)[..., None])
    base += ember[..., None] * np.array(emit_rgb)[None, None, :] * 0.10
    hgt = np.clip((f2 - f1) / 0.2, 0, 1) ** 0.4 - crack * 0.9 - finec * 0.35
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(hgt.astype(np.float32), 1), 2.4)


def feather_maps(emit_rgb, root_rgb, tip_rgb, size=1024, seed=5, barbs=52, edge=0.055, heat=1.0, rachis=0.35):
    """刃羽贴图（u 沿羽长、v 沿宽度，中脊在 v=0.5）：根暗尖亮的灰烬渐变 + 斜向羽枝细纹 + 金属中脊，
    外侧 60% 羽长的两道刃口烧成余烬（发光），中脊有一道淡淡的暗火。"""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    c = np.abs(v - 0.5) * 2
    t = np.clip((u - 0.04) / 0.9, 0, 1)
    t = t * t * (3 - 2 * t)
    phase = (u - 0.30 * c) * barbs + 0.6 * np.sin(u * 11.0 + seed)
    barb = (0.5 + 0.5 * np.sin(TAU * phase)) ** 3
    noise = box_blur(rng.random((size, size)).astype(np.float32), 3) - 0.5
    cloud = box_blur(rng.random((size, size)).astype(np.float32), 30) - 0.5
    spine = np.exp(-(c / 0.035) ** 2)
    col = np.array(root_rgb)[None, None, :] * (1 - t[..., None]) + np.array(tip_rgb)[None, None, :] * t[..., None]
    base = col * (0.84 + 0.16 * barb[..., None] + noise[..., None] * 0.25 + cloud[..., None] * 1.2)
    base = base * (1 - 0.35 * spine[..., None])
    jag = edge * np.clip(1 + (box_blur(rng.random((size, size)).astype(np.float32), 6) - 0.5) * 22, 0.3, 2.2)
    burn = np.clip((c - (1 - jag)) / np.maximum(jag, 1e-3), 0, 1) ** 1.5 * smoothstep_np(0.30, 0.85, u)
    chips = (box_blur((rng.random((size, size)) > 0.9975).astype(np.float32), 3) * 30) * smoothstep_np(0.2, 0.9, u)
    char = np.clip(burn * 1.6, 0, 1)
    base = base * (1 - 0.65 * char[..., None])
    glow = np.clip(burn + chips * (c > 0.6) + spine * rachis * smoothstep_np(0.12, 0.3, u) * (1 - smoothstep_np(0.7, 0.95, u)), 0, 1.2)
    em = np.stack([glow * ch * heat for ch in emit_rgb], axis=2)
    hgt = barb * 0.25 + spine * 1.0 - char * 0.3
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(hgt.astype(np.float32), 1), 2.0)


def flame_maps(size=256, seed=3, hot=(1.0, 0.78, 0.36), mid=(1.0, 0.34, 0.06), tip=(0.62, 0.07, 0.02), fade=0.78):
    """火舌渐变（配合 flame() 的 UV：u 绕一周、v=0 为火根）：根部金黄、中段橙、尖端暗红并变暗，
    叠一点沿火舌方向的竖纹，单色自发光的火舌远看像实心锥，渐变后才像火。"""
    rng = np.random.default_rng(seed)
    r, c = np.mgrid[0:size, 0:size].astype(np.float32) / size
    v = 1.0 - r
    streak = box_blur(rng.random((8, size)).astype(np.float32).repeat(size // 8, axis=0), 3)
    streak = (streak - 0.5) * 1.6
    w1 = smoothstep_np(0.0, 0.45, v)[..., None]
    w2 = smoothstep_np(0.40, 1.0, v)[..., None]
    col = np.array(hot)[None, None, :] * (1 - w1) + np.array(mid)[None, None, :] * w1
    col = col * (1 - w2) + np.array(tip)[None, None, :] * w2
    inten = np.clip(1.0 - fade * v ** 1.4 + streak * 0.25 * v, 0.05, 1.2)[..., None]
    em = np.clip(col * inten, 0, 1)
    base = np.clip(col * 0.25, 0, 1)
    return base, em, None


def smoothstep_np(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def forged_maps(emit_rgb, base_rgb, groove_rgb, size=1024, seed=31, dimples=18, density=9, traces=9, trace_w=1):
    """锻打暗钢（第二轮：替换满身龟裂的余烬甲面）：锤击凹坑（Voronoi 块面明暗 + 法线凹陷）
    + 卷草细雕花（沟槽压暗、填暗金）+ 边框细线 + 稀疏的余烬电路嵌线（只有嵌线发光）。"""
    from kit.core import Canvas
    rng = np.random.default_rng(seed)
    f1, _, idx = voronoi(size, dimples, rng)
    cellv = np.sin(idx * 1.9 + seed) * 0.5 + 0.5
    cloud = box_blur(rng.random((size, size)).astype(np.float32), 30) - 0.5
    grain = box_blur(rng.random((size, size)).astype(np.float32), 1) - 0.5
    # 雕花：每格一对反向卷草涡线 + 一片叶梗，格线为面板分割线
    cv = Canvas(size, size)
    cell = size / density
    for gx in range(density):
        for gy in range(density):
            cx, cy = (gx + 0.5) * cell, (gy + 0.5) * cell
            for flip in (1, -1):
                t = np.linspace(0, rng.uniform(1.2, 1.7) * TAU, 70)
                r = cell * 0.30 * np.exp(-0.24 * t)
                ph = rng.uniform(0, TAU)
                ox = cx + flip * cell * 0.18
                xs = ox + flip * r * np.cos(t + ph)
                ys = cy + r * np.sin(t + ph)
                for i in range(len(t) - 1):
                    cv.line(xs[i], ys[i], xs[i + 1], ys[i + 1], 1)
    for k in range(density + 1):
        cv.line(0, k * cell, size, k * cell, 1)
    eng = np.clip(box_blur(cv.mask, 1) * 1.5, 0, 1)
    # 余烬嵌线：少量 45° 折线，端点落在过孔上
    cv2 = Canvas(size, size)
    for _ in range(traces):
        x, y = rng.uniform(0.05, 0.95) * size, rng.uniform(0.05, 0.95) * size
        cv2.ring(x, y, 4, 1)
        for _ in range(int(rng.integers(3, 6))):
            ang = rng.choice([0, 45, 90, 135, 180, 225, 270, 315]) * math.pi / 180
            L = rng.uniform(0.04, 0.12) * size
            x2 = float(np.clip(x + math.cos(ang) * L, 8, size - 8))
            y2 = float(np.clip(y + math.sin(ang) * L, 8, size - 8))
            cv2.line(x, y, x2, y2, trace_w)
            x, y = x2, y2
        cv2.dot(x, y, 3)
    tr = np.clip(cv2.mask, 0, 1)
    tone = 0.80 + 0.26 * cellv + 0.30 * (f1 - 0.35) + cloud * 1.4 + grain * 0.10
    base = np.array(base_rgb)[None, None, :] * tone[..., None]
    base = base * (1 - eng[..., None]) + np.array(groove_rgb)[None, None, :] * eng[..., None]
    base = base * (1 - 0.6 * tr[..., None]) + np.array(emit_rgb)[None, None, :] * tr[..., None] * 0.12
    em = None
    if traces:
        halo = box_blur(tr, 3)
        em = np.clip(np.stack([np.clip(tr + halo * 0.45, 0, 1) * c for c in emit_rgb], axis=2), 0, 1)
    hgt = np.clip(f1, 0, 0.8) ** 2 * 0.9 - eng * 0.7 - tr * 0.5
    return np.clip(base, 0, 1), em, height_normal(box_blur(hgt.astype(np.float32), 1), 2.2)


def burning_blade_maps(emit_rgb, base_rgb, size=1024, seed=23, edge=0.34, hot_rgb=(1.0, 0.82, 0.50)):
    """燃烧剑刃（配合 ridge_blade 的 UV：u 沿刃长、v 横跨刃宽，v=0 / 1 为刃口）：
    余烬接缝暗钢刃身 + 两侧刃口一道炽热发光带（暗红 → 橙 → 近金白，边界成火舌状不规则起伏）。
    刃口外加火焰几何在侧视里读成锯齿，所以“燃烧”全部交给贴图与刃口发光管。"""
    base, em, nrm = ember_crack_maps(emit_rgb, base_rgb=base_rgb, size=size, seed=seed, cells=5, width=0.026,
                                     fine=0.10, heat=0.9, soot=0.45, keep=0.8)
    rng = np.random.default_rng(seed + 5)
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    c = np.abs(v - 0.5) * 2
    # 火舌状边界：沿刃长方向起伏的噪声，让发光带像一排向剑柄方向舔上来的火
    lick = box_blur(rng.random((size, size)).astype(np.float32), 10)
    wav = 0.5 + 0.5 * np.sin(u * 60.0 + (lick - 0.5) * 18.0)
    w = edge * (0.55 + 0.45 * wav) * (0.6 + 0.4 * smoothstep_np(0.0, 0.25, u))
    band = np.clip((c - (1 - w)) / np.maximum(w, 1e-3), 0, 1) ** 1.3
    k2 = smoothstep_np(0.5, 1.0, band)[..., None]
    ramp = np.array(emit_rgb)[None, None, :] * (1 - k2) + np.array(hot_rgb)[None, None, :] * k2
    em = np.clip(em + ramp * band[..., None], 0, 1)
    base = base * (1 - 0.6 * band[..., None]) + ramp * band[..., None] * 0.15
    return np.clip(base, 0, 1), em, nrm


def ember_feather_maps(emit_rgb, root_rgb, tip_rgb, size=1024, seed=5, barbs=58, edge=0.16, tip=0.50, heat=1.0,
                       hot_rgb=(1.0, 0.80, 0.46), deep_rgb=(0.50, 0.06, 0.02), rachis=0.25):
    """第二轮刃羽：灰烬黑羽根 → 炭灰羽身 → 边缘与羽尖炽热（暗红 → 橙 → 近金白的发光渐变），
    刃口发光带自根向尖逐渐变宽、边缘锯齿不规则；叠斜向羽枝细纹、金属中脊与零星火星。
    UV：u 沿羽长（0 羽根）、v 沿宽度（中脊 v=0.5）。"""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    c = np.abs(v - 0.5) * 2
    t = smoothstep_np(0.02, 0.95, u)
    phase = (u - 0.28 * c) * barbs + 0.6 * np.sin(u * 11.0 + seed)
    barb = (0.5 + 0.5 * np.sin(TAU * phase)) ** 3
    noise = box_blur(rng.random((size, size)).astype(np.float32), 3) - 0.5
    cloud = box_blur(rng.random((size, size)).astype(np.float32), 30) - 0.5
    spine = np.exp(-(c / 0.035) ** 2)
    jag = np.clip(1 + (box_blur(rng.random((size, size)).astype(np.float32), 5) - 0.5) * 20, 0.35, 2.0)
    w = edge * (0.25 + 1.5 * u) * jag
    band = np.clip((c - (1 - w)) / np.maximum(w, 1e-3), 0, 1) ** 1.2 * smoothstep_np(0.08, 0.45, u)
    tipheat = smoothstep_np(1 - tip, 1.0, u) ** 1.4 * (0.35 + 0.65 * c ** 1.5)
    hf = np.clip(np.maximum(band, tipheat), 0, 1)
    chips = box_blur((rng.random((size, size)) > 0.998).astype(np.float32), 2) * 25 * smoothstep_np(0.3, 0.9, u)
    k1 = smoothstep_np(0.0, 0.55, hf)[..., None]
    k2 = smoothstep_np(0.55, 1.0, hf)[..., None]
    ramp = np.array(deep_rgb)[None, None, :] * (1 - k1) + np.array(emit_rgb)[None, None, :] * k1
    ramp = ramp * (1 - k2) + np.array(hot_rgb)[None, None, :] * k2
    glow = np.clip(hf ** 1.1 + np.clip(chips, 0, 1) * 0.6 + spine * rachis * smoothstep_np(0.2, 0.5, u) *
                   (1 - smoothstep_np(0.75, 0.95, u)), 0, 1.2)
    em = ramp * glow[..., None] * heat
    col = np.array(root_rgb)[None, None, :] * (1 - t[..., None]) + np.array(tip_rgb)[None, None, :] * t[..., None]
    base = col * (0.82 + 0.18 * barb[..., None] + noise[..., None] * 0.25 + cloud[..., None] * 1.0)
    base = base * (1 - 0.3 * spine[..., None]) * (1 - 0.4 * hf[..., None]) + ramp * hf[..., None] * 0.18
    hgt = barb * 0.25 + spine * 1.0 - hf * 0.2
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(hgt.astype(np.float32), 1), 2.0)


def burn_cloth_maps(emit_rgb, base_rgb, line_rgb=None, size=2048, seed=51, buses=14, burn=0.11, reach=(0.30, 0.80)):
    """燃烧下摆织物：kit 电路纹（自下而上渐隐）+ 贴图底部一道锯齿状燃烧线——线上发光、线下焦黑带余烬点。"""
    base, em, nrm = circuit_maps(emit_rgb, base_rgb=base_rgb, line_rgb=line_rgb, size=size, seed=seed, buses=buses,
                                 reach=reach)
    rng = np.random.default_rng(seed + 1)
    h = size
    v = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    wav = box_blur(rng.random((1, size)).astype(np.float32).repeat(8, axis=0), 12)[0][None, :]
    front = burn * (1 + (wav - 0.5) * 3.0)
    d = v - front
    edge = np.exp(-(d / 0.010) ** 2)
    char = np.clip(-d / 0.05, 0, 1)
    embers = (rng.random((size, size)) > 0.9985).astype(np.float32) * (v < front + 0.08)
    embers = box_blur(embers, 1) * 6
    base = base * (1 - 0.75 * char[..., None]) + np.array(emit_rgb)[None, None, :] * edge[..., None] * 0.08
    add = np.clip(edge * 1.1 + char * 0.12 + embers, 0, 1.3)
    em = np.clip(em + np.stack([add * c for c in emit_rgb], axis=2), 0, 1)
    return np.clip(base, 0, 1), em, nrm


# ===== 动作写入（带缩放通道） =====
def put(rig, pose, frame):
    """写一帧姿态：kit 的旋转 / 位移关键帧 + pose["_scale"] 里的逐骨均匀缩放（火舌燃起、羽刃发射后隐去）。"""
    rig.put_pose(pose, frame)
    sc = pose.get("_scale", {})
    for name in getattr(rig, "scaled", ()):
        pb = rig.obj.pose.bones[name]
        v = max(1e-3, sc.get(name, 1.0))
        pb.scale = (v, v, v)
        pb.keyframe_insert("scale", frame=frame, group=name)


def loop(rig, name, frames, fn, step=1):
    """循环动作：fn(t) 的 t 从 0 走到 2π，首尾同相位。"""
    rig.new_action(name)
    for f in range(0, frames + 1, step):
        put(rig, fn(TAU * f / frames), f + 1)


def sampled(rig, name, frames, fn):
    """一次性动作：fn(帧号) 逐帧重算（帧号 1..frames+1），手臂 IK 每帧精确求解。"""
    rig.new_action(name)
    for f in range(1, frames + 2):
        put(rig, fn(f), f)


# ===== 参数轨道 =====
def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t)
    return t ** 3


EASE = {"lin": lambda t: clamp(t), "io": ease, "out": ease_out, "in": ease_in}


def _lerp_any(a, b, t):
    if isinstance(a, (int, float)):
        return lerp(a, b, t)
    if isinstance(a, Vector):
        return a.lerp(b, t)
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


def track(keys, frame):
    """参数轨道：keys 为 [(帧, 参数字典, 缓动名), ...]，缓动作用于“到达该键”的那一段。"""
    if frame <= keys[0][0]:
        return dict(keys[0][1])
    for (f0, p0, _), (f1, p1, e) in zip(keys, keys[1:]):
        if frame <= f1:
            t = EASE[e]((frame - f0) / max(1e-6, f1 - f0))
            return {k: _lerp_any(p0[k], p1[k], t) for k in p0}
    return dict(keys[-1][1])


def with_defaults(base, keys):
    """把每个关键参数字典补齐为 base 的完整副本，方便只写变化量。"""
    return [(f, {**base, **p}, e) for f, p, e in keys]


def mat_slerp(m, t):
    """把旋转矩阵 m 按比例 t 缩放（与单位阵球面插值）。"""
    q = m.to_quaternion()
    if q.w < 0:
        q.negate()
    return I3.to_quaternion().slerp(q, t).to_matrix()


# ===== 自检 =====
class Clearance:
    """动作穿插自检（复制自 _grace_helpers.Clearance）：刚性件采样点与身体胶囊体的最小间隙，全部用 pose 数学求值。
    groups 让每个采样点只和指定标签组的胶囊比较（剑只查身体与长袍、羽毛只查身体）。"""

    def __init__(self):
        self.points, self.caps = [], []

    def point(self, bone, p, tag, group="body"):
        self.points.append((bone, Vector(p), tag, group))

    def capsule(self, bone, a, b, r, tag, group="body"):
        self.caps.append((bone, Vector(a), Vector(b), r, tag, group))

    @staticmethod
    def world(rig, pose, bone, p, cache):
        return rig.head(pose, bone, cache) + rig.delta(pose, bone, cache) @ (p - rig.SEG[bone][0])

    def gap(self, rig, pose, groups):
        cache = {}
        caps = [(self.world(rig, pose, b, a, cache), self.world(rig, pose, b, c, cache), r, tag, grp)
                for b, a, c, r, tag, grp in self.caps]
        best = (1e9, "", "")
        for bone, p, tag, pg in self.points:
            w = self.world(rig, pose, bone, p, cache)
            for a, c, r, ctag, cg in caps:
                if cg not in groups.get(pg, ()):
                    continue
                ab = c - a
                t = clamp((w - a).dot(ab) / max(ab.length_squared, 1e-12))
                g = (w - a.lerp(c, t)).length - r
                if g < best[0]:
                    best = (g, tag, ctag)
        return best

    def report(self, rig, clip, poses, groups):
        worst = (1e9, "", "", 0)
        for i, pose in enumerate(poses):
            g, a, b = self.gap(rig, pose, groups)
            if g < worst[0]:
                worst = (g, a, b, i)
        print(f"MOTION CLEARANCE {clip}: min gap {worst[0] * 100:.1f} cm ({worst[1]} vs {worst[2]}) "
              f"sample {worst[3]}/{len(poses)}")
        return worst


def seam_check(rig, clips):
    """循环动作首尾帧的最大骨旋转差（度）与位移 / 缩放差，应为 0（复制自 _bossA_common.seam_check）。"""
    scene = bpy.context.scene
    for clip in clips:
        act = bpy.data.actions[clip]
        rig.obj.animation_data.action = act
        first, last = map(int, act.frame_range)
        snap = []
        for f in (first, last):
            scene.frame_set(f)
            snap.append({pb.name: (pb.matrix.to_quaternion(), pb.matrix.to_translation(), pb.matrix.to_scale())
                         for pb in rig.obj.pose.bones})
        worst, where, move = 0.0, "", 0.0
        for name, (qa, ta, sa) in snap[0].items():
            qb, tb, sb = snap[1][name]
            ang = math.degrees(qa.rotation_difference(qb).angle)
            ang = min(ang, 360 - ang)
            if ang > worst:
                worst, where = ang, name
            move = max(move, (ta - tb).length, (sa - sb).length)
        print(f"MOTION CHECK+ {clip}: loop seam {worst:.2f} deg / {move:.4f} m {where}")


def stats(ctx, target=85000, keep=("inlay", "glow", "hem", "trim", "core", "flame"), min_mesh=3000):
    """按材质统计三角面、预估游戏版减面比例（模拟 kit.rig.export 的规则：蒙皮件按材质合并、挂骨件按骨 + 材质合并）
    与静止包围盒。"""
    groups = {}
    for o, _ in ctx.parts:
        groups.setdefault(("skin", o.data.materials[0].name), []).append(o)
    for o, bone, keep_name in ctx.attached:
        key = ("att", bone, o.name) if keep_name else ("att", bone, o.data.materials[0].name)
        groups.setdefault(key, []).append(o)
    by_mat, fixed, big = {}, 0, 0
    fixed_mat = {}
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for key, objs in groups.items():
        n = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
        name = " ".join(str(k) for k in key[1:]).lower()
        by_mat[key[-1]] = by_mat.get(key[-1], 0) + n
        if n > min_mesh and not any(k in name for k in keep):
            big += n
        else:
            fixed += n
            mk = key[-1] if key[0] == "skin" else objs[0].data.materials[0].name
            fixed_mat[mk] = fixed_mat.get(mk, 0) + n
        for o in objs:
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                lo = Vector(map(min, lo, w))
                hi = Vector(map(max, hi, w))
    total = fixed + big
    ratio = clamp((target - fixed) / big, 0.12, 1.0) if big and total > target else 1.0
    print(f"TRIS {ctx.id}: total {total}  fixed {fixed}  decimatable {big}  est game ratio {ratio:.3f}")
    for k, v in sorted(by_mat.items(), key=lambda kv: -kv[1])[:24]:
        print(f"    {v:7d}  {k}")
    print("  fixed by material:")
    for k, v in sorted(fixed_mat.items(), key=lambda kv: -kv[1])[:16]:
        print(f"    {v:7d}  {k}")
    import os
    import re
    if os.environ.get("B7_DEBUG"):
        stems = {}
        for o in [o for o, _ in ctx.parts] + [o for o, _, _ in ctx.attached]:
            stem = re.sub(r"[\d.\-]+|\b[LR]\b", "", o.name).strip() + " | " + o.data.materials[0].name[11:]
            stems[stem] = stems.get(stem, 0) + sum(len(p.vertices) - 2 for p in o.data.polygons)
        for k, v in sorted(stems.items(), key=lambda kv: -kv[1])[:400]:
            print(f"  STEM {v:7d}  {k}")
    size = hi - lo
    print(f"BBOX {ctx.id}: lo ({lo.x:.2f}, {lo.y:.2f}, {lo.z:.2f}) hi ({hi.x:.2f}, {hi.y:.2f}, {hi.z:.2f}) "
          f"size ({size.x:.2f} x {size.y:.2f} x {size.z:.2f}) m")
