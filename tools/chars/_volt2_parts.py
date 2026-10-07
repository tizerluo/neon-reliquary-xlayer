"""沃尔特第二轮返工的私有部件（只给 tools/chars/volt.py 用；_forge_helpers 与莫德雷德共用，不改）。

- etch_maps：高密度细电路刻纹（1 px 线宽、45° 折线、过孔小环，低对比；可让部分走线微微发光）
- texel_uv：按世界尺寸重排 UV，保证贴图每 tile 米重复一次（kit 的 surface UV 是整块 0..1，雕花会被放大成大圈）
- cop：带中脊、铆钉与中心线圈的造型甲杯（护膝 / 护肘）
- fan：侧翼扇片（多瓣轮廓 + 银滚边 + 铆钉）
- arc_plate：四边都带银滚边的弧形肢甲片（kit.limb_plate 只在上下缘加滚边）
- zigzag：沿肢体外侧的闪电折线嵌线
"""

import math

import numpy as np
from mathutils import Vector

from kit.core import (TAU, Canvas, box_blur, ellipsoid, finish, height_normal, lerp, orient, plate, ring_points,
                      smoothstep, surface, trim)
from kit.humanoid import limb_frame


# ===== 贴图 =====
def etch_maps(base_rgb, groove_rgb, emit_rgb=None, size=1024, seed=5, cells=16, glow_share=0.25, grain=0.6):
    """细电路刻纹：每格一组 1–3 条平行走线（直 → 45° → 直，同步折角）收在过孔小环上，每 4 格一道分区细线。
    沟槽只比底色略暗（低对比），glow_share 比例的走线组写进发光图（emit_rgb 为 None 时不发光）。"""
    rng = np.random.default_rng(seed)
    cv, gl = Canvas(size, size), Canvas(size, size)
    c = size / cells
    dirs = ((1, 0), (0, 1), (-1, 0), (0, -1))
    lo, hi = 4.0, size - 5.0
    pitch = 5.0

    def inside(x, y):
        return lo < x < hi and lo < y < hi
    for gx in range(cells):
        for gy in range(cells):
            x, y = (gx + rng.uniform(0.15, 0.85)) * c, (gy + rng.uniform(0.15, 0.85)) * c
            d = int(rng.integers(4))
            turn = int(rng.choice([-1, 1]))
            lanes = int(rng.choice([1, 2, 2, 3]))
            segs = []
            for seg in range(3):
                dx, dy = dirs[d]
                if seg == 1:                                       # 中段 45° 折角
                    ndx, ndy = dirs[(d + turn) % 4]
                    dx, dy = (dx + ndx) * 0.7071, (dy + ndy) * 0.7071
                elif seg == 2:
                    dx, dy = dirs[(d + turn) % 4]
                segs.append((dx, dy, rng.uniform(0.25, 0.55) * c))
            canv = (cv, gl) if rng.random() < glow_share else (cv,)
            px, py = -dirs[d][1], dirs[d][0]                       # 首段的垂直方向，用来排开平行走线
            for k in range(lanes):
                xx, yy = x + px * pitch * k, y + py * pitch * k
                pts = [(xx, yy)]
                for dx, dy, L in segs:
                    xx, yy = xx + dx * L, yy + dy * L
                    pts.append((xx, yy))
                if not all(inside(*p) for p in pts):
                    continue
                for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                    for cc in canv:
                        cc.line(x0, y0, x1, y1, 1)
                for cc in canv:
                    cc.ring(pts[-1][0], pts[-1][1], 2.2, 1)
    for k in range(0, size, int(c * 4)):                           # 分区细线（像板件拼缝）
        cv.line(0, k + 2, size - 1, k + 2, 1)
        cv.line(k + 2, 0, k + 2, size - 1, 1)
    mask = np.clip(box_blur(cv.mask, 1) * 1.3, 0, 1)
    g = box_blur(rng.random(mask.shape).astype(np.float32), 18) - 0.5
    tone = 1.0 + g * grain
    base = np.stack([base_rgb[i] * tone * (1 - mask) + groove_rgb[i] * mask for i in range(3)], axis=2)
    em = None
    if emit_rgb:
        gm = np.clip(box_blur(gl.mask, 1) * 1.2, 0, 1)
        em = np.clip(np.stack([gm * ch for ch in emit_rgb], axis=2), 0, 1)
    return np.clip(base, 0, 1), em, height_normal(-mask, 1.4)


def texel_uv(obj, tile):
    """把对象 UV 缩放成每 tile 米重复一次贴图（u、v 分别按平均世界长度计算；u 方向取整，闭合环不出接缝）。"""
    me = obj.data
    if not me.uv_layers:
        return obj
    uv = me.uv_layers.active.data
    su = sv = wsum = 0.0
    for poly in me.polygons:
        li = list(poly.loop_indices)
        if len(li) < 3:
            continue
        p0, p1, p2 = (me.vertices[me.loops[i].vertex_index].co for i in li[:3])
        t0, t1, t2 = (uv[i].uv for i in li[:3])
        e1, e2 = p1 - p0, p2 - p0
        a, b = t1.x - t0.x, t2.x - t0.x
        c, d = t1.y - t0.y, t2.y - t0.y
        det = a * d - b * c
        if abs(det) < 1e-12:
            continue
        pu = (e1 * d - e2 * c) / det                               # 每单位 u 的世界位移
        pv = (e2 * a - e1 * b) / det
        w = poly.area
        su += pu.length * w
        sv += pv.length * w
        wsum += w
    if wsum <= 0:
        return obj
    su, sv = su / wsum / tile, sv / wsum / tile
    if su > 1.5:
        su = round(su)
    for layer in me.uv_layers:
        for dd in layer.data:
            dd.uv = (dd.uv[0] * su, dd.uv[1] * sv)
    return obj


# ===== 甲杯与扇片 =====
def cop(ctx, name, c, fwd, up, rx, rz, depth, mat, spec, trim_mat, glow_mat, keel=0.010, thick=0.005,
        rivets=6, nu=32, nv=9, boss=0.016, wrap=0.0):
    """造型甲杯：椭圆轮廓前凸，上下各一道中脊，外缘微微回卷；银滚边 + 铆钉 + 中心小线圈（银环叠发光芯）。
    wrap 让左右两侧向后包（贴住圆柱形的肢体，侧看不露缝）。"""
    f = Vector(fwd).normalized()
    u = Vector(up)
    u = (u - f * u.dot(f)).normalized()
    x = u.cross(f)

    def h(px, pz, r):
        k = keel * math.exp(-(px / (0.16 * rx)) ** 2) * smoothstep(0.22 * rz, 0.65 * rz, abs(pz)) * (1 - r * r) ** 0.35
        return depth * (1 - r * r) ** 0.55 + k - 0.18 * depth * smoothstep(0.82, 1.0, r) - wrap * (px / rx) ** 2

    def pt(uu, vv, lift=0.0):
        th = uu * TAU
        r = lerp(0.03, 1.0, vv)
        px, pz = math.cos(th) * rx * r, math.sin(th) * rz * r
        return c + x * px + u * pz + f * (h(px, pz, r) + lift)
    obj = surface(name, pt, nu, nv, [mat], closed_u=True)
    orient(obj, lambda q: c - f * 0.08)
    ctx.part(finish(obj, thick, 0, 0), spec)
    ctx.part(trim(f"{name} rim", [pt(i / 40, 1.0, 0.0015) for i in range(40)], 0.0026, trim_mat, closed=True), spec)
    for i in range(rivets):
        th = (i + 0.5) / rivets
        ctx.part(ellipsoid(f"{name} rivet {i}", pt(th, 0.80, 0.0018), (0.0038,) * 3, [trim_mat], 8, 5), spec)
    top = c + f * (depth + 0.002)
    ctx.part(trim(f"{name} boss", ring_points(top, f, boss, 18), 0.0030, trim_mat, closed=True), spec)
    ctx.part(trim(f"{name} boss coil", ring_points(top + f * 0.003, f, boss * 0.62, 14), 0.0022, trim_mat, closed=True),
             spec)
    ctx.part(ellipsoid(f"{name} core", top + f * 0.002, (boss * 0.42, boss * 0.42, boss * 0.42), [glow_mat], 10, 6),
             spec)
    return pt


def fan(ctx, name, origin, back, up, size, mat, trim_mat, spec, bow=0.0, outward=None, lobes=4, depth=0.004):
    """侧翼扇片：自枢轴向后展开的多瓣扇形（瓣尖 / 凹口交替），银滚边 + 枢轴铆钉；bow 让扇面末端朝 outward 翘起。"""
    xa = Vector(back).normalized()
    ya = Vector(up)
    ya = (ya - xa * ya.dot(xa)).normalized()
    na = xa.cross(ya)                                              # plate() 的挤出法向
    face = 1.0 if outward is None or na.dot(Vector(outward)) >= 0 else -1.0
    bow *= face                                                    # 弯曲与滚边都朝外侧
    n = lobes * 2 - 1
    outline = [(0.0, -0.30 * size)]
    for i in range(n):
        phi = lerp(-1.05, 1.05, i / (n - 1))
        rr = size * ((0.78 if i in (0, n - 1) else 1.0) if i % 2 == 0 else 0.62)
        outline.append((rr * math.cos(phi), rr * math.sin(phi)))
    outline.append((0.0, 0.30 * size))
    bulge = (lambda px, py: bow * (px / size) ** 2) if bow else None
    ctx.part(plate(name, outline, depth, [mat], origin=origin, xaxis=xa, yaxis=ya, bulge=bulge, bev=0.0008), spec)
    o = Vector(origin)
    edge = [o + xa * px + ya * py + na * (bow * (px / size) ** 2 + face * depth * 0.5) for px, py in outline]
    ctx.part(trim(f"{name} edge", edge, 0.0020, trim_mat, closed=True), spec)
    for i in range(1, n, 2):                                      # 瓣间肋线（枢轴 → 凹口）
        px, py = outline[i + 1]
        rib = [o + (xa * px + ya * py) * t + na * (bow * (px * t / size) ** 2 + face * depth * 0.5)
               for t in (0.18, 0.55, 0.92)]
        ctx.part(trim(f"{name} rib {i}", rib, 0.0014, trim_mat), spec)
    ctx.part(ellipsoid(f"{name} pivot", o + na * face * depth * 0.6, (0.0055,) * 3, [trim_mat], 10, 6), spec)


def arc_plate(ctx, name, a, b, r0, r1, out, arc, mat, trim_mat, spec, thick=0.005, ridge=0.0, bulge=0.0,
              nu=18, nv=6, trim_r=0.0022, sides=True, arc1=None, point=0.0):
    """包裹肢体段 a→b 的弧形甲片，四边银滚边（kit.limb_plate 只有上下缘）。返回 pt(u, v, lift)。
    arc1 为 b 端半张角（收窄成梯形），point 让 b 端下缘中间凸出成尖（占段长比例）。"""
    axis, o, w = limb_frame(a, b, out)
    arc1 = arc if arc1 is None else arc1

    def pt(uu, vv, lift=0.0):
        th = (2 * uu - 1) * lerp(arc, arc1, vv)
        vv = vv * (1 + point * (1 - abs(2 * uu - 1)) ** 1.5) if point else vv
        cc = a.lerp(b, vv)
        r = lerp(r0, r1, vv) + bulge * math.sin(vv * math.pi) + ridge * math.exp(-(th / 0.30) ** 2) + lift
        return cc + (o * math.cos(th) + w * math.sin(th)) * r

    def on_axis(q):
        t = max(0.0, min(1.0, (q - a).dot(b - a) / (b - a).length_squared))
        return a + (b - a) * t
    obj = surface(name, lambda uu, vv: pt(uu, vv), nu, nv, [mat])
    orient(obj, on_axis)
    ctx.part(finish(obj, thick, 1, 0), spec)
    lift = thick * 1.25
    for vv in (0.0, 1.0):
        ctx.part(trim(f"{name} rim {vv}", [pt(i / (nu + 5), vv, lift) for i in range(nu + 6)], trim_r, trim_mat), spec)
    if sides:
        for uu in (0.0, 1.0):
            ctx.part(trim(f"{name} side {uu}", [pt(uu, j / 8, lift) for j in range(9)], trim_r, trim_mat), spec)
    return pt


def zigzag(a, b, o, w, radius_fn, teeth=5, amp=0.12, v0=0.08, v1=0.92, per=3):
    """肢体外侧的闪电折线：沿 a→b 分 teeth 段，在 o/w 平面内左右交替偏 amp 弧度，radius_fn(v) 给贴面半径。"""
    corners = [(lerp(v0, v1, k / teeth), amp * (1 if k % 2 else -1) * (0.0 if k in (0, teeth) else 1.0))
               for k in range(teeth + 1)]
    pts = []
    for (va, ta), (vb, tb) in zip(corners, corners[1:]):
        for i in range(per):
            t = i / per
            v, th = lerp(va, vb, t), lerp(ta, tb, t)
            pts.append(a.lerp(b, v) + (o * math.cos(th) + w * math.sin(th)) * radius_fn(v))
    v = corners[-1][0]
    pts.append(a.lerp(b, v) + o * radius_fn(v))
    return pts
