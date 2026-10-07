"""Boss 6 · 剧毒三位体 私有工具（只被 tools/chars/boss_6.py 与 _b6_parts.py 引用，不属于公共工具包 kit）。

- 带 UV 的扫掠管 / 超椭球 / 车削件（kit 的 tube、ellipsoid 没有 UV，鳞片 / 雕花贴图会糊成一点）
- 平行传输中心线 Spine：颈、尾、腿的蒙皮管、背甲片、收口环共用同一套标架
- 局部标架摆放（头部 / 储罐在局部坐标建模后整体摆到世界）
- 带缩放通道的动作写入（储罐爆亮、毒雾喷射、毒滴拉伸；kit.rig 只写旋转与位移）
- 参数轨道、三次贝塞尔颈链求解（给定颈根切向与头部位置 / 朝向，按骨长依次放关节）
- 运动检查（地面、循环接缝、三颈互相穿插）、面数与包围盒统计、毒液气泡贴图
部分函数复制自 _bossA_common / _bossB_common（只读参考）并按本角色改写。
"""

import math

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_point_line

from kit.core import (TAU, box_blur, catmull, clamp, frame_from, height_normal, lerp, orient, surface,
                      transform, voronoi)

KEEP = ("inlay", "glow", "hem", "trim", "core")


def sgnpow(x, k):
    return math.copysign(abs(x) ** k, x)


def orth(v, axis):
    """v 去掉沿 axis 的分量后归一化。"""
    v = Vector(v)
    a = Vector(axis)
    w = v - a * v.dot(a)
    return w.normalized() if w.length > 1e-8 else w


def rot(v, axis, angle):
    return Matrix.Rotation(angle, 3, Vector(axis).normalized()) @ Vector(v)


# ===== 标架摆放 =====
def frame_matrix(origin, fwd, up, scale=1.0):
    """局部（+Y 前、+Z 上、+X 右）→ 世界的 4x4 矩阵。"""
    return Matrix.Translation(Vector(origin)) @ frame_from(fwd, up).to_4x4() @ Matrix.Scale(scale, 4)


def place(obj, origin, fwd, up=(0, 0, 1), scale=1.0):
    return transform(obj, frame_matrix(origin, fwd, up, scale))


# ===== 带 UV 的基础体 =====
def path_frames(pts, up=(0, 0, 1)):
    """折线的平行传输标架：返回 (切向, 法向, 副法向)。"""
    m = len(pts)
    T = [(pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(m)]
    N = transport(T, up)
    return T, N, [t.cross(n) for t, n in zip(T, N)]


def transport(tangents, n0):
    """沿切向序列平行传输初始法向 n0。"""
    out = []
    n = Vector(n0)
    for t in tangents:
        w = n - t * n.dot(t)
        if w.length < 1e-6:
            w = out[-1] if out else (Vector((1, 0, 0)) - t * t.x)
        n = w.normalized()
        out.append(n)
    return out


def sweep(name, points, radii, mats, n=16, per=4, fx=1.0, fy=1.0, up=(0, 0, 1), tile=None, shape=None):
    """带 UV 的扫掠管：u 绕截面、v 沿路径；tile 为贴图一格的米数；shape(a, t) 为截面半径倍率。"""
    pts, rad = catmull([Vector(p) for p in points], list(radii), per) if per > 1 else \
        ([Vector(p) for p in points], list(radii))
    T, N, Bn = path_frames(pts, up)
    m = len(pts)
    acc = [0.0]
    for i in range(1, m):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    L = acc[-1] or 1.0

    def idx(v):
        return min(m - 1, int(round(v * (m - 1))))

    def fn(u, v):
        j = idx(v)
        a = u * TAU
        r = rad[j] * (shape(a, acc[j] / L) if shape else 1.0)
        return pts[j] + N[j] * (math.cos(a) * r * fx) + Bn[j] * (math.sin(a) * r * fy)
    uvfn = None
    if tile:
        circ = TAU * max(rad) * (fx + fy) * 0.5
        ru = max(1, round(circ / tile))
        uvfn = lambda u, v: (u * ru, acc[idx(v)] / tile)   # noqa: E731
    return surface(name, fn, n, m, mats, closed_u=True, uvfn=uvfn)


def blob(name, center, radii, mats, nu=24, nv=14, power=2.0, frame=None, shape=None, tile=None):
    """带 UV 的超椭球：power>2 更方；frame 为 3x3 朝向（列为局部 x/y/z）；shape(p_local) 为额外径向外扩。"""
    c = Vector(center)
    M = frame or Matrix.Identity(3)
    e = 2.0 / power

    def fn(u, v):
        a = u * TAU
        phi = math.pi * v
        sx, cx = math.sin(phi), math.cos(phi)
        local = Vector((sgnpow(sx, e) * sgnpow(math.sin(a), e) * radii[0],
                        sgnpow(sx, e) * sgnpow(math.cos(a), e) * radii[1],
                        sgnpow(cx, e) * radii[2]))
        if shape:
            d = local.normalized() if local.length > 1e-9 else Vector((0, 0, 1))
            local = local + d * shape(local)
        return c + M @ local
    uvfn = None
    if tile:
        ru = max(1, round(TAU * max(radii[0], radii[1]) / tile))
        uvfn = lambda u, v: (u * ru, (1 - v) * math.pi * radii[2] / tile)   # noqa: E731
    obj = surface(name, fn, nu, nv, mats, closed_u=True, uvfn=uvfn)
    return orient(obj, lambda q: c)


def lathe_y(name, profile, mats, seg=24, uv=None, a0=0.0, a1=TAU):
    """沿局部 +Y 的车削体：profile 为 [(半径, y), ...]；返回局部坐标网格，再用 place 摆放。"""
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
    return orient(obj, lambda q: Vector((0, q.y, 0)))


def circle_y(r, y, n=32, phase=0.0):
    """局部 +Y 轴上高度 y 处的一圈点。"""
    return [Vector((math.sin(phase + TAU * i / n) * r, y, math.cos(phase + TAU * i / n) * r)) for i in range(n)]


# ===== 平行传输中心线 =====
class Spine:
    """中心线：pts/radii 为控制点（Catmull 细分）；D 为背侧法向（由 up 起算沿线传输），B = T×D 为侧向。
    pt(t, a, extra) 取弧长比例 t 处、绕轴角 a（0 为背侧，+π/2 为 B 侧）的表面点。"""

    def __init__(self, pts, radii, up, per=6):
        P, Rr = catmull([Vector(p) for p in pts], list(radii), per)
        m = len(P)
        T = [(P[min(i + 1, m - 1)] - P[max(i - 1, 0)]).normalized() for i in range(m)]
        self.P, self.R, self.T = P, Rr, T
        self.D = transport(T, up)
        self.Bn = [t.cross(d) for t, d in zip(T, self.D)]
        acc = [0.0]
        for i in range(1, m):
            acc.append(acc[-1] + (P[i] - P[i - 1]).length)
        self.acc, self.L = acc, acc[-1]

    def frame(self, t):
        """弧长比例 t（可超出 [0,1]，按端点切向外推）处的 (中心, T, D, B, 半径)。"""
        s = t * self.L
        if s <= 0:
            return self.P[0] + self.T[0] * s, self.T[0], self.D[0], self.Bn[0], self.R[0]
        if s >= self.L:
            return self.P[-1] + self.T[-1] * (s - self.L), self.T[-1], self.D[-1], self.Bn[-1], self.R[-1]
        acc = self.acc
        lo, hi = 0, len(acc) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if acc[mid] <= s:
                lo = mid
            else:
                hi = mid
        f = (s - acc[lo]) / max(1e-9, acc[hi] - acc[lo])
        c = self.P[lo].lerp(self.P[hi], f)
        T = self.T[lo].lerp(self.T[hi], f).normalized()
        D = orth(self.D[lo].lerp(self.D[hi], f), T)
        return c, T, D, T.cross(D), lerp(self.R[lo], self.R[hi], f)

    def pt(self, t, a, extra=0.0, rscale=1.0):
        c, T, D, Bn, r = self.frame(t)
        return c + (D * math.cos(a) + Bn * math.sin(a)) * (r * rscale + extra)

    def near(self, q):
        """离 q 最近的中心线点（法线朝向判定用）。"""
        return min(self.P, key=lambda p: (p - q).length_squared)


def spine_tube(name, sp, mats, n=24, nv=None, t0=0.0, t1=1.0, extra=0.0, tile=None, shape=None):
    """沿 Spine 的蒙皮管（带 UV）：shape(a, t) 为截面半径倍率。"""
    nv = nv or max(8, int((t1 - t0) * sp.L / 0.05))

    def fn(u, v):
        t = lerp(t0, t1, v)
        a = u * TAU
        c, T, D, Bn, r = sp.frame(t)
        k = shape(a, t) if shape else 1.0
        return c + (D * math.cos(a) + Bn * math.sin(a)) * (r * k + extra)
    uvfn = None
    if tile:
        ru = max(1, round(TAU * max(sp.R) / tile))
        uvfn = lambda u, v: (u * ru, lerp(t0, t1, v) * sp.L / tile)   # noqa: E731
    obj = surface(name, fn, n, nv, mats, closed_u=True, uvfn=uvfn)
    return orient(obj, sp.near)


def spine_shell(name, sp, t0, t1, a0, a1, off0, off1, mats, nu=12, nv=6, arch=0.0):
    """Spine 上的弧形甲片（未加厚）：t0→t1 沿线，a0→a1 绕轴；off0/off1 为两端离表面的高度；
    arch 让甲片中线额外拱起。"""
    def fn(u, v):
        t = lerp(t0, t1, v)
        a = lerp(a0, a1, u)
        return sp.pt(t, a, lerp(off0, off1, v) + arch * math.sin(math.pi * u))
    obj = surface(name, fn, nu, nv, mats)
    return orient(obj, sp.near)


def surf_normal(f, a, b, ref, eps=1e-3):
    """参数曲面 f(a, b) 的外法线（按 ref 点判定朝外）。"""
    p = f(a, b)
    n = (f(a + eps, b) - f(a - eps, b)).cross(f(a, b + eps) - f(a, b - eps))
    if n.length < 1e-12:
        n = p - ref
    n.normalize()
    return n if n.dot(p - ref) >= 0 else -n


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
    """一次性动作：fn(帧号) 逐帧重算（帧号 1 … frames+1）。"""
    rig.new_action(name)
    for f in range(1, frames + 2, step):
        put(rig, fn(f), f)


# ===== 缓动与参数轨道 =====
def ease_io(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_in(t):
    return clamp(t) ** 2.4


def ease_out(t):
    return 1 - (1 - clamp(t)) ** 2.4


def ease_back(t):
    """先略回拉再冲出（蓄力后弹射）。"""
    t = clamp(t)
    return t * t * (2.6 * t - 1.6)


EASE = {"io": ease_io, "in": ease_in, "out": ease_out, "back": ease_back, "lin": clamp}


def lerp_params(a, b, t):
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k, b.get(k)), b.get(k, a.get(k))
        if isinstance(va, (int, float)):
            out[k] = lerp(va, vb, t)
        else:
            out[k] = tuple(lerp(x, y, t) for x, y in zip(va, vb))
    return out


def track(keys, frame):
    """参数轨道：keys 为 [(帧, 参数字典, 缓动名), ...]，缓动作用于“到达该键”的那一段。"""
    if frame <= keys[0][0]:
        return dict(keys[0][1])
    for (f0, p0, _), (f1, p1, e) in zip(keys, keys[1:]):
        if frame <= f1:
            return lerp_params(p0, p1, EASE[e]((frame - f0) / max(1e-6, f1 - f0)))
    return dict(keys[-1][1])


def with_defaults(base, keys):
    return [(f, {**base, **p}, e) for f, p, e in keys]


# ===== 颈链求解 =====
def bezier_pts(p0, p1, p2, p3, n):
    out = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        out.append(p0 * (mt * mt * mt) + p1 * (3 * mt * mt * t) + p2 * (3 * mt * t * t) + p3 * (t * t * t))
    return out


def _chord(a, b, cur, L):
    """线段 a→b 上离 cur 恰为 L 的点（取靠 b 的解）。"""
    d = b - a
    w = a - cur
    A = d.dot(d)
    if A < 1e-12:
        return b.copy()
    B = 2 * w.dot(d)
    C = w.dot(w) - L * L
    s = clamp((-B + math.sqrt(max(0.0, B * B - 4 * A * C))) / (2 * A))
    return a + d * s


def walk(pts, lengths, ext):
    """沿折线按弦长依次放关节；折线用尽时沿 ext 外推。
    返回 (关节, 剩余弧长)：> 0 表示曲线比骨链长，< 0 表示骨链超出曲线末端。"""
    joints = [pts[0].copy()]
    cur, k, n = pts[0], 1, len(pts)
    over = 0.0
    for L in lengths:
        while k < n and (pts[k] - cur).length < L:
            k += 1
        if k >= n:
            w = pts[-1] - cur
            b = 2 * w.dot(ext)
            c = w.dot(w) - L * L
            x = (-b + math.sqrt(max(0.0, b * b - 4 * c))) / 2
            cur = pts[-1] + ext * x
            over = x
            joints.append(cur)
            continue
        cur = _chord(pts[k - 1], pts[k], cur, L)
        joints.append(cur)
    if over > 0:
        return joints, -over
    rem = (pts[k] - cur).length if k < n else 0.0
    for i in range(k, n - 1):
        rem += (pts[i + 1] - pts[i]).length
    return joints, rem


def solve_chain(p0, t0, p3, hd, lengths, bow, a=0.42, b=0.36, n=90, iters=22):
    """颈链曲线：三次贝塞尔（颈根沿 t0 出发、以 hd 方向到达 p3）+ 沿 bow 方向的 sin² 拱起（两端斜率为 0，
    不改变颈根与头部朝向）。骨链比曲线长时二分拱起幅度，比曲线短时二分缩短把手。
    长把手的纯贝塞尔在“骨链 / 弦长”> 1.3 时会折叠、逐节弦长行走会跳变，拱起法在盘颈姿态下仍连续。
    返回 (关节列表, 拱起幅度米数；负值表示把手缩短比例 - 1)。"""
    p0, p3 = Vector(p0), Vector(p3)
    t0, hd = Vector(t0).normalized(), Vector(hd).normalized()
    D = max(1e-4, (p3 - p0).length)
    nb = orth(bow, (p3 - p0) / D)
    bump = [math.sin(math.pi * i / n) ** 2 for i in range(n + 1)]

    def run(k, A):
        pts = bezier_pts(p0, p0 + t0 * (D * a * k), p3 - hd * (D * b * k), p3, n)
        if A:
            pts = [p + nb * (A * w) for p, w in zip(pts, bump)]
        return walk(pts, lengths, hd)
    j, r = run(1.0, 0.0)
    if r > 0:
        lo, hi = 0.02, 1.0
        j, r = run(lo, 0.0)
        if r >= 0:
            return j, lo - 1.0
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            j, r = run(mid, 0.0)
            if r > 0:
                hi = mid
            else:
                lo = mid
        k = 0.5 * (lo + hi)
        return run(k, 0.0)[0], k - 1.0
    lo, hi = 0.0, 1.6 * D
    j, r = run(1.0, hi)
    if r <= 0:
        return j, hi
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        j, r = run(1.0, mid)
        if r > 0:
            hi = mid
        else:
            lo = mid
    A = 0.5 * (lo + hi)
    return run(1.0, A)[0], A


def chain_dorsals(joints, d0):
    """沿骨链关节平行传输背侧向量：返回每节骨的背侧（与骨方向正交）。"""
    out = []
    d = Vector(d0)
    for j in range(len(joints) - 1):
        t = (joints[j + 1] - joints[j]).normalized()
        d = orth(d, t)
        out.append(d.copy())
    return out


# ===== 检查 =====
def _seg_dist(p, a, b):
    q, f = intersect_point_line(p, a, b)
    f = clamp(f)
    return (p - a.lerp(b, f)).length


def seg_seg(a0, a1, b0, b1, k=6):
    """两线段近似最近距离（端点 + 内分点对另一段求点线距）。"""
    best = 1e9
    for i in range(k + 1):
        t = i / k
        best = min(best, _seg_dist(a0.lerp(a1, t), b0, b1), _seg_dist(b0.lerp(b1, t), a0, a1))
    return best


def ground_check(rig, clips, bones, offset=0.0, label="ground"):
    """逐帧统计给定骨（头尾两端）的最低高度，offset 为骨到部件底面的距离。"""
    scene = bpy.context.scene
    for clip in clips:
        act = bpy.data.actions[clip]
        rig.obj.animation_data.action = act
        f0, f1 = map(int, act.frame_range)
        lo = (1e9, "", 0)
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            for b in bones:
                pb = rig.obj.pose.bones[b]
                z = min(pb.head.z, pb.tail.z) - (offset(b) if callable(offset) else offset)
                if z < lo[0]:
                    lo = (z, b, f)
        print(f"MOTION CHECK+ {clip}: min {label} clearance {lo[0]:.3f} m at {lo[1]} frame {lo[2]}")


def seam_check(rig, clips):
    """循环动作首尾帧的最大骨旋转差（度）与位移 / 缩放差，应为 0。"""
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


def clearance_check(rig, clips, groups, statics=()):
    """骨段组之间的最小间隙（中心距减半径和）：groups 为 {组名: [(骨名, 半径), ...]}，
    statics 为静止胶囊 [(名, a, b, 半径)]（储罐等挂在躯干上的部件，随 Chest 变换）。"""
    scene = bpy.context.scene
    names = list(groups)
    for clip in clips:
        act = bpy.data.actions[clip]
        rig.obj.animation_data.action = act
        f0, f1 = map(int, act.frame_range)
        worst = (1e9, "", 0)
        worst_s = (1e9, "", 0)
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            segs = {g: [(rig.obj.pose.bones[b].head.copy(), rig.obj.pose.bones[b].tail.copy(), r, b)
                        for b, r in groups[g]] for g in names}
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    for a0, a1, ra, na in segs[names[i]]:
                        for b0, b1, rb, nb in segs[names[j]]:
                            d = seg_seg(a0, a1, b0, b1, 4) - ra - rb
                            if d < worst[0]:
                                worst = (d, f"{na}~{nb}", f)
            chest = rig.obj.pose.bones["Chest"].matrix @ rig.obj.data.bones["Chest"].matrix_local.inverted()
            for sname, sa, sb, rs in statics:
                wa, wb = chest @ Vector(sa), chest @ Vector(sb)
                for g in names:
                    for a0, a1, ra, na in segs[g]:
                        d = seg_seg(a0, a1, wa, wb, 4) - ra - rs
                        if d < worst_s[0]:
                            worst_s = (d, f"{na}~{sname}", f)
        print(f"MOTION CHECK+ {clip}: min neck-neck clearance {worst[0]:.3f} m ({worst[1]} frame {worst[2]})")
        if statics:
            print(f"MOTION CHECK+ {clip}: min neck-tank clearance {worst_s[0]:.3f} m ({worst_s[1]} frame {worst_s[2]})")


# ===== 近景审图（B6_CLOSEUP=1 时由配方调用；kit 的 detail 视角对准包围盒顶部中央，拍不到三颗头） =====
def closeup(cid, shots, accent, tag="close"):
    """shots: [(名, 相机位置, 目标点, 焦距), ...]；灯光与相机沿用 kit.review 的布置。"""
    import os
    from kit import review
    from kit.core import ROOT
    samples = int(os.environ.get("CHAR_SAMPLES", 24))
    size = int(os.environ.get("CHAR_SIZE", 600))
    scene, camera = review._setup(accent, samples, size)
    review._lights(Vector((0, 0.3, 3.0)), 5.2, accent)
    out = ROOT / "art" / "review" / "chars" / cid
    out.mkdir(parents=True, exist_ok=True)
    for name, loc, target, lens in shots:
        camera.location = Vector(loc)
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = lens
        path = out / f"{cid}-{tag}-{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print("REVIEW", path)


# ===== 统计 =====
def stats(ctx, target=85000, keep=KEEP, detail=False):
    """按材质的三角面统计、预计游戏版减面比例与静止包围盒；detail=True 时列出不减面材质里最重的部件类。"""
    import re
    by = {}
    cat = {}
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    objs = [o for o, _ in ctx.parts] + [o for o, *_ in ctx.attached]
    for o in objs:
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        m = o.data.materials[0].name if o.data.materials else "?"
        by[m] = by.get(m, 0) + n
        if detail and any(w in m.lower() for w in keep):
            key = re.sub(r"[-\d.]+", "", o.name.replace(ctx.title, "")).strip() + " | " + m.split()[-1]
            cat[key] = cat.get(key, 0) + n
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    total = sum(by.values())
    kept = sum(v for k, v in by.items() if any(w in k.lower() for w in keep))
    rest = total - kept
    ratio = clamp((target - kept) / rest, 0.12, 1.0) if rest and total > target else 1.0
    print(f"TRIS {ctx.id}: total {total}  keep {kept}  rest {rest}  est game ratio {ratio:.3f}")
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
        print(f"    {v:7d}  {k}")
    for k, v in sorted(cat.items(), key=lambda kv: -kv[1])[:40]:
        print(f"      keep {v:6d}  {k}")
    size = hi - lo
    print(f"BBOX {ctx.id}: lo ({lo.x:.2f}, {lo.y:.2f}, {lo.z:.2f}) hi ({hi.x:.2f}, {hi.y:.2f}, {hi.z:.2f}) "
          f"size ({size.x:.2f} x {size.y:.2f} x {size.z:.2f}) m")


# ===== 贴图 =====
def venom_maps(emit_rgb, base_rgb=(0.03, 0.16, 0.07), size=512, seed=3):
    """毒液：横向可平铺的上涌流纹（两层频率）+ 大小不一、只出现在部分格子的气泡环 + 细碎小泡；
    亮暗对比拉开，避免整面均匀发白。"""
    rng = np.random.default_rng(seed)
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    stream = 0.5 + 0.5 * np.sin(xs * TAU * 3 + np.sin(ys * TAU * 2 + xs * TAU) * 1.6)
    stream2 = 0.5 + 0.5 * np.sin(xs * TAU * 7 - ys * TAU * 3 + np.sin(xs * TAU * 2) * 2.0)
    f1, _, idx = voronoi(size, 6, rng)
    h = (np.sin(idx * 12.9898) * 43758.5453) % 1.0
    rr = 0.10 + 0.16 * h
    ring = np.clip(1 - np.abs(f1 - rr) / 0.028, 0, 1) * (h > 0.35)
    fine, _, fidx = voronoi(size, 18, rng)
    fh = (np.sin(fidx * 78.233) * 43758.5453) % 1.0
    dots = np.clip(1 - fine / (0.05 + 0.10 * fh), 0, 1) ** 2 * (fh > 0.5)
    fill = np.clip(0.22 + 0.38 * stream * (0.6 + 0.4 * stream2) + 0.55 * ring + 0.45 * dots, 0, 1.2)
    em = np.stack([fill * c for c in emit_rgb], axis=2)
    base = np.stack([base_rgb[i] * (0.6 + 0.7 * stream) + ring * 0.10 for i in range(3)], axis=2)
    hgt = box_blur((ring * 0.6 + dots * 0.4).astype(np.float32), 1)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(hgt, 1.2)
