"""Boss 4（机械神祇）私有工具：网格小工具（环带、回转壳、分区材质网格、定向椭球）、可平铺符文带贴图、
带缩放通道的动作写入、参数轨道与旋转积分、骨链登记、动作检查与面数统计。

只被 tools/chars/boss_4.py 引用。部分函数复制自 _bossB_common / _bossA_common（按规则只读不改，复制后按需改写）。
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from kit.core import (TAU, Canvas, _finish, bm_object, clamp, ellipsoid, finish, frame_from, lerp, orient,
                      surface, transform, tube)
from kit.rig import I3

KEEP = ("inlay", "glow", "hem", "trim", "core", "halo")


# ===== 基础几何 =====
def mirror(v, side):
    """把右侧（+X）定义的点镜像到 side 侧。"""
    v = Vector(v)
    return Vector((v.x * side, v.y, v.z))


def gauss(x, c, s):
    return math.exp(-((x - c) / s) ** 2)


def ring_at(c, au, av, r, a):
    """环上一点：a=0 在 av 方向，a 增大转向 au。"""
    return Vector(c) + Vector(au) * (math.sin(a) * r) + Vector(av) * (math.cos(a) * r)


def circle(c, au, av, r, n, phase=0.0):
    return [ring_at(c, au, av, r, phase + TAU * i / n) for i in range(n)]


def arc(c, au, av, r, a0, a1, n):
    return [ring_at(c, au, av, r, a0 + (a1 - a0) * i / (n - 1)) for i in range(n)]


def axis_frame(d, up=(0, 0, 1)):
    """以 d 为轴的两条正交径向（与 frame_from 一致：x、z 列）。"""
    f = frame_from(d, up)
    return f.col[0].copy(), f.col[2].copy()


def ring_around(a, b, t, r, n=24, up=(0, 0, 1)):
    """绕线段 a→b 的第 t 处一圈点（肢体上的金箍 / 滚边）。"""
    a, b = Vector(a), Vector(b)
    x, z = axis_frame((b - a).normalized(), up)
    c = a.lerp(b, t)
    return [c + (x * math.cos(TAU * i / n) + z * math.sin(TAU * i / n)) * r for i in range(n)]


def place(obj, origin, direction, up=(0, 0, 1)):
    """把局部坐标（+Y 前、+Z 上）的网格摆到世界：原点 origin、+Y 对齐 direction。"""
    m = Matrix.Translation(Vector(origin)) @ frame_from(direction, up).to_4x4()
    return transform(obj, m)


def ellip(name, c, radii, axes, mats, seg=16, rings=10):
    """任意朝向的椭球：axes 为三条局部轴（世界方向），radii 为对应半径。"""
    obj = ellipsoid(name, (0, 0, 0), radii, mats, seg, rings)
    ax, ay, az = (Vector(v).normalized() for v in axes)
    m = Matrix((ax, ay, az)).transposed().to_4x4()
    m.translation = Vector(c)
    return transform(obj, m)


def grid(name, fn, us, vs, mats, closed_u=False, matfn=None, uvfn=None):
    """显式 u / v 采样列表的参数网格（可非均匀分布）；matfn(i, j) 给每个面指定材质槽（做金边等分区）。"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows = [[bm.verts.new(fn(u, v)) for u in us] for v in vs]
    nu = len(us)
    ucoord = list(us) + ([1.0] if closed_u else [])
    for j in range(len(vs) - 1):
        for i in range(nu if closed_u else nu - 1):
            i2 = (i + 1) % nu
            try:
                f = bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            except ValueError:
                continue
            if matfn:
                f.material_index = matfn(i, j)
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                u, v = ucoord[ii], vs[jj]
                loop[uvl].uv = uvfn(u, v) if uvfn else (u, 1 - v)
    return bm_object(name, bm, mats)


def lin(a, b, n):
    return [lerp(a, b, i / (n - 1)) for i in range(n)]


def sweep(name, a, b, rfn, mats, nu=24, nv=10, up=(0, 0, 1), t0=0.0, t1=1.0, phi0=None, phi1=None,
          uv=(1.0, 1.0), matfn=None, vs=None):
    """绕线段 a→b 的回转壳：rfn(t, phi) 返回半径（t 沿轴 0..1，phi=0 指向 up 在截面上的分量）。
    phi0/phi1 给定时只做局部扇形（不闭合），用于护肩甲片等。"""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    dn = d / L
    x, z = axis_frame(dn, up)
    closed = phi0 is None
    us = [i / nu for i in range(nu)] if closed else [i / (nu - 1) for i in range(nu)]
    vs = vs or [j / (nv - 1) for j in range(nv)]

    def pt(u, v):
        phi = u * TAU if closed else lerp(phi0, phi1, u)
        t = lerp(t0, t1, v)
        r = rfn(t, phi)
        return a + dn * (t * L) + (z * math.cos(phi) + x * math.sin(phi)) * r
    obj = grid(name, pt, us, vs, mats, closed_u=closed, matfn=matfn,
               uvfn=lambda u, v: (u * uv[0], (1 - v) * uv[1]))
    return orient(obj, lambda c: a + dn * (c - a).dot(dn))


def lathe_y(name, profile, mats, seg=24, uv=None, a0=0.0, a1=TAU):
    """沿局部 +Y 轴的车削体：profile 为 [(半径, y), ...]（按顺序连成母线），返回局部坐标网格，再用 place 摆放。"""
    full = abs(a1 - a0 - TAU) < 1e-6
    n = len(profile)

    def pt(u, v):
        f = v * (n - 1)
        i = min(n - 2, int(f))
        t = f - i
        r = lerp(profile[i][0], profile[i + 1][0], t)
        y = lerp(profile[i][1], profile[i + 1][1], t)
        a = a0 + u * (a1 - a0)
        return Vector((math.sin(a) * r, y, math.cos(a) * r))
    obj = surface(name, pt, seg, (n - 1) * 2 + 1, mats, closed_u=full, uvfn=uv)
    orient(obj, lambda q: Vector((0, q.y, 0)))
    return obj


def band(name, c, au, av, r0, r1, mats, seg=96, thick=0.02, uv=None, bulge=0.0, a0=0.0, a1=TAU, nv=3, sub=0):
    """平面环带（符文环 / 光环板）：r0 内径、r1 外径，沿法向加厚 thick；uv(u, v) 自定义贴图坐标（v=0 外缘）。"""
    c, au, av = Vector(c), Vector(au).normalized(), Vector(av).normalized()
    nrm = au.cross(av)
    full = abs(a1 - a0 - TAU) < 1e-6

    def pt(u, v):
        a = a0 + u * (a1 - a0)
        return ring_at(c, au, av, lerp(r1, r0, v), a) + nrm * (bulge * math.sin(math.pi * v))
    obj = surface(name, pt, seg, nv, mats, closed_u=full, uvfn=uv)
    return finish(obj, thick, 0, sub)


def cyl_band(name, c, rx, ry, z0, z1, mats, seg=64, thick=0.02, uv=None, flare=0.0, nv=3, sub=0):
    """竖直筒形环带（腰带 / 符文箍）：z0 顶、z1 底，flare 为底边外扩。"""
    c = Vector(c)

    def pt(u, v):
        a = u * TAU
        g = 1 + flare * v
        return Vector((c.x + rx * g * math.sin(a), c.y + ry * g * math.cos(a), lerp(z0, z1, v)))
    obj = surface(name, pt, seg, nv, mats, closed_u=True, uvfn=uv)
    orient(obj, lambda q: Vector((c.x, c.y, q.z)))
    return finish(obj, thick, 1, sub)


def densify(pts, step):
    """把折线按 step 米加密（投射到曲面前用，保证细管贴合）。"""
    out = [Vector(pts[0])]
    for a, b in zip(pts, pts[1:]):
        a, b = Vector(a), Vector(b)
        n = max(1, int(math.ceil((b - a).length / step)))
        out += [a.lerp(b, i / n) for i in range(1, n + 1)]
    return out


# ===== 贴图 =====
def rune_glyph(rng):
    """如尼式字形（单位方格内的线段）：中央竖干 + 2–3 道斜枝 / 横枝，避免读成拉丁字母。"""
    segs = [(0.5, 0.0, 0.5, 1.0)]
    for _ in range(int(rng.integers(2, 4))):
        y = float(rng.choice([0.2, 0.4, 0.6, 0.8]))
        sd = float(rng.choice([-1.0, 1.0]))
        kind = rng.random()
        if kind < 0.6:
            segs.append((0.5, y, 0.5 + sd * 0.42, y + float(rng.choice([-0.28, 0.28]))))
        else:
            segs.append((0.5, y, 0.5 + sd * 0.40, y))
            segs.append((0.5 + sd * 0.40, y, 0.5 + sd * 0.40, y - 0.18))
    if rng.random() < 0.35:
        segs.append((0.2, 0.5, 0.8, 0.5))
    return segs


def rune_strip_maps(emit_rgb, base_rgb, line_rgb=None, w=1024, h=512, cols=2, aspect=1.6, seed=13, glyph=0.50,
                    stroke=7):
    """横向可平铺的符文带：上下双边线 + 一行几何字形 + 字间菱点。
    aspect 为一个贴图周期在模型上的“长 / 宽”比，用来把字形在模型上校正成方形。"""
    rng = np.random.default_rng(seed)
    pad = w // 8                       # 左右留白画布：越界的笔画卷回另一侧，保证横向无缝平铺
    cv = Canvas(w + 2 * pad, h)
    for y, lw in ((0.07, 3), (0.15, 2), (0.85, 2), (0.93, 3)):
        cv.line(0, h * y, w + 2 * pad - 1, h * y, lw)
    gh = h * glyph
    gw = gh * (w / h) / aspect
    cw = w / cols
    for c in range(cols):
        x0, y0 = pad + c * cw + (cw - gw) / 2, (h - gh) / 2
        for (a, b, cc, d) in rune_glyph(rng):
            cv.line(x0 + a * gw, y0 + b * gh, x0 + cc * gw, y0 + d * gh, stroke)
        if rng.random() < 0.45:                                    # 字脚小圆
            cy = y0 + (0.0 if rng.random() < 0.5 else 1.0) * gh
            cv.ring(x0 + 0.5 * gw, cy, gh * 0.09, 2)
        xm, ym, r = pad + c * cw, h * 0.5, h * 0.07
        dx = r * (w / h) / aspect
        for (p0, p1) in (((xm - dx, ym), (xm, ym + r)), ((xm, ym + r), (xm + dx, ym)),
                         ((xm + dx, ym), (xm, ym - r)), ((xm, ym - r), (xm - dx, ym))):
            cv.line(p0[0], p0[1], p1[0], p1[1], 3)
    big = cv.mask
    mask = big[:, pad:pad + w].copy()
    mask[:, :pad] = np.maximum(mask[:, :pad], big[:, pad + w:])
    mask[:, w - pad:] = np.maximum(mask[:, w - pad:], big[:, :pad])
    mask = np.clip(mask, 0, 1)
    line_rgb = line_rgb or tuple(ch * 0.2 for ch in emit_rgb)
    return _finish(mask, np.ones_like(mask), rng, emit_rgb, base_rgb, line_rgb, sparkle=False)


def sunburst_maps(emit_rgb, base_rgb, rays=16, size=512):
    """日轮贴图（配合车削体 UV：u 绕圈、v 由中心向外）：中心炽白、向外渐暗，叠加 rays 道放射光芒。"""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    u, v = xs, 1.0 - ys
    ray = (0.5 + 0.5 * np.cos(u * TAU * rays)) ** 6
    fine = (0.5 + 0.5 * np.cos(u * TAU * rays * 2 + math.pi)) ** 10 * 0.5
    core = np.clip(1.0 - v / 0.35, 0, 1) ** 0.8
    glow = np.clip(core + (ray + fine) * (1 - v) ** 1.5 * 0.9 + 0.12, 0, 1.2)
    em = np.stack([glow * c for c in emit_rgb], axis=2)
    base = np.stack([np.full_like(glow, base_rgb[i]) * (0.7 + 0.3 * glow) for i in range(3)], axis=2)
    nrm = np.zeros((size, size, 3), np.float32)
    nrm[..., 2] = 1.0
    return np.clip(base, 0, 1), np.clip(em, 0, 1), nrm * 0.5 + 0.5


# ===== 动作工具 =====
def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t)
    return t ** 3


EASE = {"io": ease, "in": ease_in, "out": ease_out, "lin": lambda t: clamp(t)}


def lerp_params(a, b, t):
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k, b.get(k)), b.get(k, a.get(k))
        if isinstance(va, (int, float)):
            out[k] = lerp(va, vb, t)
        else:
            out[k] = Vector(va).lerp(Vector(vb), t)
    return out


def track(keys, frame):
    """参数轨道：keys 为 [(帧, 参数字典, 缓动名), ...]，缓动作用于“到达该键”的那一段。"""
    if frame <= keys[0][0]:
        return dict(keys[0][1])
    for (f0, p0, _), (f1, p1, e) in zip(keys, keys[1:]):
        if frame <= f1:
            t = (frame - f0) / max(1e-6, f1 - f0)
            return lerp_params(p0, p1, EASE[e](t))
    return dict(keys[-1][1])


def with_defaults(base, keys):
    """把每个关键参数字典补齐为 base 的完整副本，只写变化量。"""
    out, cur = [], dict(base)
    for f, p, e in keys:
        cur = {**base, **p}
        out.append((f, cur, e))
    return out


def spin_curve(rate, total, steps=480):
    """把角速度曲线 rate(s) 积分，并归一化为 s=1 时正好转过 total 弧度（一次性动作首尾与待机对齐）。"""
    acc = [0.0]
    for i in range(steps):
        acc.append(acc[-1] + max(0.0, rate((i + 0.5) / steps)) / steps)
    k = total / acc[-1] if acc[-1] > 1e-9 else 0.0

    def angle(s):
        f = clamp(s) * steps
        i = min(steps - 1, int(f))
        return (acc[i] + (acc[i + 1] - acc[i]) * (f - i)) * k
    return angle


def slerp_m(a, b, t):
    """两个旋转矩阵的球面插值（None 视为单位阵）。"""
    qa = (a if a is not None else I3).to_quaternion()
    qb = (b if b is not None else I3).to_quaternion()
    if qa.dot(qb) < 0:
        qb.negate()
    return qa.slerp(qb, clamp(t)).to_matrix()


def post(pose, name, m):
    """在已有局部旋转之后叠加 m（绕静止骨架轴再转一次）。"""
    pose[name] = m @ pose.get(name, I3)


def raise_axis(d):
    """让方向 d 向上抬的水平轴。"""
    n = Vector(d).cross(Vector((0, 0, 1)))
    return n.normalized() if n.length > 1e-6 else Vector((1, 0, 0))


def hinge(d1, d2):
    """两段肢体方向的弯曲轴：绕它正转使夹角增大（更弯）。"""
    n = Vector(d1).cross(Vector(d2))
    return n.normalized() if n.length > 1e-6 else Vector((1, 0, 0))


# ===== 动作写入（带缩放通道） =====
def put(rig, pose, frame):
    rig.put_pose(pose, frame)
    sc = pose.get("_scale", {})
    for name in getattr(rig, "scaled", ()):
        pb = rig.obj.pose.bones[name]
        v = sc.get(name, 1.0)
        pb.scale = (v, v, v) if isinstance(v, (int, float)) else tuple(v)
        pb.keyframe_insert("scale", frame=frame, group=name)


def loop(rig, name, frames, fn, step=1):
    """循环动作：fn(t) 的 t 从 0 走到 2π（首尾同相位）。"""
    rig.new_action(name)
    for f in range(0, frames + 1, step):
        put(rig, fn(TAU * f / frames), f + 1)


def sampled(rig, name, frames, fn, step=1):
    """一次性动作：fn(帧号) 逐帧重算（帧号从 1 到 frames+1）。"""
    rig.new_action(name)
    for f in range(1, frames + 2, step):
        put(rig, fn(f), f)


class ChainSet:
    """kit.rig.motion_check 只看 g.prefix / g.K / g.J：骨名须为 {prefix}{k}.{j}（j 从 1 到 J）。"""

    def __init__(self, prefix, K, J):
        self.prefix, self.K, self.J = prefix, K, J


# ===== 检查 =====
def seam_check(rig, clips, sym=None):
    """循环动作首尾帧的最大骨旋转差（度）与位移 / 缩放差；sym={骨: 对称步进角} 的骨再报告按几何对称折算后的差。"""
    scene = bpy.context.scene
    sym = sym or {}
    for clip in clips:
        act = bpy.data.actions[clip]
        rig.obj.animation_data.action = act
        first, last = map(int, act.frame_range)
        snap = []
        for f in (first, last):
            scene.frame_set(f)
            snap.append({pb.name: (pb.matrix.to_quaternion(), pb.matrix.to_translation(), pb.matrix.to_scale())
                         for pb in rig.obj.pose.bones})
        worst, where, move, sym_worst = 0.0, "", 0.0, 0.0
        for name, (qa, ta, sa) in snap[0].items():
            qb, tb, sb = snap[1][name]
            ang = math.degrees(qa.rotation_difference(qb).angle)
            ang = min(ang, 360 - ang)
            if name in sym:
                step = sym[name]
                m = ang % step
                sym_worst = max(sym_worst, min(m, step - m))
                continue
            if ang > worst:
                worst, where = ang, name
            move = max(move, (ta - tb).length, (sa - sb).length)
        print(f"MOTION CHECK+ {clip}: loop seam {worst:.2f} deg / {move:.4f} m {where}; "
              f"halo seam (mod symmetry) {sym_worst:.2f} deg")


def clearance(rig, clips, tips):
    """逐帧统计给定骨尾端（龙骨 / 线缆 / 甲片末端）的最低高度，查悬浮离地。tips 为 [(骨名, 末端下方余量)]。"""
    scene = bpy.context.scene
    for clip in clips:
        act = bpy.data.actions[clip]
        rig.obj.animation_data.action = act
        f0, f1 = map(int, act.frame_range)
        lo = (1e9, "", 0)
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            for b, off in tips:
                z = rig.obj.pose.bones[b].tail.z - off
                if z < lo[0]:
                    lo = (z, b, f)
        print(f"MOTION CHECK+ {clip}: min hover clearance {lo[0]:.3f} m at {lo[1]} frame {lo[2]}")


def stats(ctx, target=85000, keep=KEEP):
    """打印按材质的三角面统计、预计游戏版减面比例与静止包围盒。"""
    by = {}
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    objs = [o for o, _ in ctx.parts] + [o for o, *_ in ctx.attached]
    hidden = set(ctx.hidden)
    for o in objs + list(ctx.hidden):
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        m = o.data.materials[0].name if o.data.materials else "?"
        if o in hidden:
            m = "(hidden) " + m
        by[m] = by.get(m, 0) + n
        if o.hide_render:
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    total = sum(v for k, v in by.items() if not k.startswith("(hidden)"))
    kept = sum(v for k, v in by.items() if any(w in k.lower() for w in keep) and not k.startswith("(hidden)"))
    rest = total - kept
    ratio = clamp((target - kept) / rest, 0.12, 1.0) if rest and total > target else 1.0
    print(f"TRIS {ctx.id}: total {total}  keep {kept}  rest {rest}  est game ratio {ratio:.3f}")
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
        print(f"    {v:7d}  {k}")
    size = hi - lo
    print(f"BBOX {ctx.id}: lo ({lo.x:.2f}, {lo.y:.2f}, {lo.z:.2f}) hi ({hi.x:.2f}, {hi.y:.2f}, {hi.z:.2f}) "
          f"size ({size.x:.2f} x {size.y:.2f} x {size.z:.2f}) m")
