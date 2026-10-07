"""Boss B 组（boss-4 … boss-7）私有工具：环带 / 弧点、局部标架摆放、车削件、动作参数轨道、
旋转积分、姿态混合（支持位移向量）、面数与包围盒统计。

只被 tools/chars/boss_4.py … boss_7.py 引用，不属于公共工具包 tools/kit。
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from kit.core import (TAU, bm_object, clamp, finish, frame_from, lerp, orient, plate, smoothstep, surface,
                      transform, trim, tube)
from kit.rig import I3, R

KEEP = ("inlay", "glow", "hem", "trim", "core")


# ===== 几何小工具 =====
def ring_at(c, au, av, r, a):
    """环上一点：a=0 在 av 方向，a 增大转向 au。"""
    return Vector(c) + Vector(au) * (math.sin(a) * r) + Vector(av) * (math.cos(a) * r)


def arc(c, au, av, r, a0, a1, n):
    return [ring_at(c, au, av, r, a0 + (a1 - a0) * i / (n - 1)) for i in range(n)]


def circle(c, au, av, r, n, phase=0.0):
    return [ring_at(c, au, av, r, phase + TAU * i / n) for i in range(n)]


def band(name, c, au, av, r0, r1, mats, seg=96, thick=0.02, uv=None, bulge=0.0, a0=0.0, a1=TAU, nv=3, sub=0):
    """平面环带（符文环 / 光环板）：r0 内径、r1 外径，沿法向加厚 thick；uv(u, v) 自定义贴图坐标。"""
    c, au, av = Vector(c), Vector(au).normalized(), Vector(av).normalized()
    nrm = au.cross(av)
    full = abs(a1 - a0 - TAU) < 1e-6

    def pt(u, v):
        a = a0 + u * (a1 - a0)
        return ring_at(c, au, av, lerp(r1, r0, v), a) + nrm * (bulge * math.sin(math.pi * v))
    obj = surface(name, pt, seg, nv, mats, closed_u=full, uvfn=uv)
    return finish(obj, thick, 0, sub)


def cyl_band(name, c, rx, ry, z0, z1, mats, seg=64, thick=0.02, uv=None, flare=0.0, nv=3, sub=0):
    """竖直筒形环带（冠带 / 腰带 / 符文箍）：z0 顶、z1 底，flare 为底边外扩。"""
    c = Vector(c)

    def pt(u, v):
        a = u * TAU
        g = 1 + flare * v
        return Vector((c.x + rx * g * math.sin(a), c.y + ry * g * math.cos(a), lerp(z0, z1, v)))
    obj = surface(name, pt, seg, nv, mats, closed_u=True, uvfn=uv)
    orient(obj, lambda q: Vector((c.x, c.y, q.z)))
    return finish(obj, thick, 1, sub)


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


def place(obj, origin, direction, up=(0, 0, 1)):
    """把局部坐标（+Y 前、+Z 上）的网格摆到世界：原点 origin、+Y 对齐 direction。"""
    m = Matrix.Translation(Vector(origin)) @ frame_from(direction, up).to_4x4()
    return transform(obj, m)


def axis_frame(d, up=(0, 0, 1)):
    """以 d 为轴的两条正交径向（与 frame_from 一致：x、z 列）。"""
    f = frame_from(d, up)
    return f.col[0].copy(), f.col[2].copy()


def ring_around(a, b, t, r, n=24, up=(0, 0, 1)):
    """绕线段 a→b 的第 t 处一圈点（用于肢体上的金箍 / 滚边）。"""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    x, z = axis_frame(d, up)
    c = a.lerp(b, t)
    return [c + (x * math.cos(TAU * i / n) + z * math.sin(TAU * i / n)) * r for i in range(n)]


def limb(name, a, b, prof, mats, n=16, up=(0, 0, 1)):
    """沿直线 a→b 的肢体甲管：prof 为 [(t, 半径), ...]，半径 0 处收尖。"""
    a, b = Vector(a), Vector(b)
    pts = [a.lerp(b, t) for t, _ in prof]
    return tube(name, pts, [r for _, r in prof], mats, n=n, up=up, per=2)


def lancet(w, h, bot=0.0, n=8, tip=1.0):
    """哥特尖拱形轮廓（x 横向，y 向上），底宽 w，高 h；bot 为底边下凹量。"""
    pts = [(-w / 2, 0.0)]
    for i in range(1, n + 1):
        t = i / n
        pts.append((-w / 2 * (1 - t ** 1.6) * (1 - 0.15 * math.sin(math.pi * t)), h * (t ** 0.85) * tip if i < n else h))
    for i in range(n - 1, 0, -1):
        t = i / n
        pts.append((w / 2 * (1 - t ** 1.6) * (1 - 0.15 * math.sin(math.pi * t)), h * (t ** 0.85) * tip))
    pts.append((w / 2, 0.0))
    if bot:
        pts.append((0.0, -bot))
    return pts


def blade_outline(L, w, back=0.35, n=10, curve=0.0):
    """刃羽轮廓：x 沿长度 0→L，y 为宽；前缘弧、后缘直，尖端收尖；curve 使整体弯成弧。"""
    top, low = [], []
    for i in range(1, n):
        t = i / n
        c = curve * L * math.sin(math.pi * t) * 0.5
        wt = w * min(1.0, (t / 0.15) ** 0.6) * (1 - smoothstep(0.5, 1.0, t)) ** 0.8
        top.append((t * L, c + wt * (1 - back)))
        low.append((t * L, c - wt * back))
    return [(0.0, 0.0)] + top + [(L, 0.0)] + list(reversed(low))


def sub_plate(name, outline, depth, mats, origin, xaxis, yaxis, bulge=None, bev=0.0):
    """plate 的薄包装（统一倒角段数）。"""
    return plate(name, outline, depth, mats, origin=origin, xaxis=xaxis, yaxis=yaxis, bulge=bulge, bev=bev, bev_seg=1)


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


class Track:
    """关键参数轨道：keys=[(s, 值), ...]（s∈[0,1]），相邻关键之间平滑插值；值可为数或元组。
    每个关键可带第三项自定义缓动函数，作用于它到下一关键的区段。"""

    def __init__(self, keys, shape=ease):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.shape = shape

    def __call__(self, s):
        ks = self.keys
        if s <= ks[0][0]:
            return ks[0][1]
        for k0, k1 in zip(ks, ks[1:]):
            s0, v0, s1, v1 = k0[0], k0[1], k1[0], k1[1]
            if s <= s1:
                f = k0[2] if len(k0) > 2 else self.shape
                t = f((s - s0) / max(1e-9, s1 - s0))
                if isinstance(v0, tuple):
                    return tuple(lerp(a, b, t) for a, b in zip(v0, v1))
                return lerp(v0, v1, t)
        return ks[-1][1]


def spin_curve(rate, total, steps=480):
    """把角速度曲线 rate(s) 积分，并归一化为 s=1 时正好转过 total 弧度（保证一次性动作首尾与待机对齐）。"""
    acc = [0.0]
    for i in range(steps):
        acc.append(acc[-1] + max(0.0, rate((i + 0.5) / steps)) / steps)
    k = total / acc[-1] if acc[-1] > 1e-9 else 0.0

    def angle(s):
        f = clamp(s) * steps
        i = min(steps - 1, int(f))
        return (acc[i] + (acc[i + 1] - acc[i]) * (f - i)) * k
    return angle


def mix(a, b, t):
    """两个姿态逐项混合：矩阵球面插值、浮点与向量线性插值（kit.motion.blend 不支持向量位移）。"""
    if t <= 0.0:
        return dict(a)
    if t >= 1.0:
        return dict(b)
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k), b.get(k)
        if isinstance(va, (int, float)) or isinstance(vb, (int, float)):
            out[k] = lerp(va or 0.0, vb or 0.0, t)
        elif isinstance(va, Vector) or isinstance(vb, Vector):
            va = va if va is not None else Vector((0, 0, 0))
            vb = vb if vb is not None else Vector((0, 0, 0))
            out[k] = va.lerp(vb, t)
        else:
            qa = (va or I3).to_quaternion()
            qb = (vb or I3).to_quaternion()
            if qa.dot(qb) < 0:
                qb.negate()
            out[k] = qa.slerp(qb, t).to_matrix()
    return out


def chain_mix(poses, weights):
    """按权重序列依次混合：poses[0] 起，逐个以 weights[i] 混向 poses[i+1]。"""
    p = poses[0]
    for q, w in zip(poses[1:], weights):
        p = mix(p, q, w)
    return p


def pre(pose, name, m):
    """在已有局部旋转之前叠加 m（m 作用在骨自身静止系之后，即先 m 后原值）。"""
    pose[name] = pose.get(name, I3) @ m


def post(pose, name, m):
    """在已有局部旋转之后叠加 m（绕静止骨架轴再转一次）。"""
    pose[name] = m @ pose.get(name, I3)


def hinge(d1, d2):
    """两段肢体方向的弯曲轴：绕它正转使夹角增大（更弯）。"""
    n = Vector(d1).cross(Vector(d2))
    return n.normalized() if n.length > 1e-6 else Vector((1, 0, 0))


def raise_axis(d):
    """让方向 d 向上抬的水平轴。"""
    n = Vector(d).cross(Vector((0, 0, 1)))
    return n.normalized() if n.length > 1e-6 else Vector((1, 0, 0))


# ===== 统计 =====
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
