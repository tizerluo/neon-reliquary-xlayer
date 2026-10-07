"""Boss 5（零域先知 · 腐化祭坛）私有工具：八棱台体、方截面放样、带 UV 的扫掠管、杏仁眼、平面环带、
局部标架椭球、动作参数轨道 / 旋转积分 / 姿态混合、骨骼缩放关键帧、面数与包围盒统计。

动作工具与统计改写自 tools/chars/_bossB_common.py（只读参考，未修改）；只被 tools/chars/boss_5.py 引用。
"""

import math

import bmesh
from mathutils import Matrix, Vector

from kit.core import (TAU, apply_all, auto_smooth, bevel, bm_object, catmull, clamp, ellipsoid, lerp, orient, plate,
                      solidify, spike, surface, transform, trim)
from kit.rig import I3

KEEP = ("inlay", "glow", "hem", "trim", "core", "eye")


# ===== 几何 =====
def prism(name, rings, mats, sides=8, phase=math.pi / 8, uv=2.0, caps=(True, True), cap_mats=(0, 0), bev=0.0,
          sx=1.0, sy=1.0):
    """正多棱台：rings 为自下而上的 [(外接半径, z), ...]；phase=π/8 时八棱台的一个平面正对 +Y。
    侧面按弧长（米）/ uv 展开贴图坐标，bev 为棱边倒角宽度（单段），倒角后按角度拆分法线保持硬朗切面。"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows = []
    for r, z in rings:
        rows.append([bm.verts.new((math.sin(phase + TAU * i / sides) * r * sx,
                                   math.cos(phase + TAU * i / sides) * r * sy, z)) for i in range(sides)])
    for j in range(len(rows) - 1):
        (r0, z0), (r1, z1) = rings[j], rings[j + 1]
        l0, l1 = 2 * r0 * math.sin(math.pi / sides), 2 * r1 * math.sin(math.pi / sides)
        for i in range(sides):
            i2 = (i + 1) % sides
            try:
                f = bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            except ValueError:
                continue
            f.material_index = 0
            for loop, (uu, vv) in zip(f.loops, ((i * l0, z0), ((i + 1) * l0, z0), ((i + 1) * l1, z1), (i * l1, z1))):
                loop[uvl].uv = (uu / uv, vv / uv)
    for k, row in enumerate((rows[0], rows[-1])):
        if not caps[k]:
            continue
        try:
            f = bm.faces.new(row)
        except ValueError:
            continue
        f.material_index = cap_mats[k]
        for loop in f.loops:
            loop[uvl].uv = (loop.vert.co.x / uv, loop.vert.co.y / uv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = bm_object(name, bm, mats, smooth=False)
    if bev:
        bevel(obj, bev, 1, 30)
        apply_all(obj)
    return auto_smooth(obj, 20)


def oct_points(r, z, sides=8, phase=math.pi / 8, sx=1.0, sy=1.0):
    return [Vector((math.sin(phase + TAU * i / sides) * r * sx, math.cos(phase + TAU * i / sides) * r * sy, z))
            for i in range(sides)]


def sq(hw, z, ch=0.28, jit=None, hy=None):
    """倒角方截面（8 点，逆时针）：hw 半宽、ch 为倒角占比；jit(i) 给每个顶点的 z 抖动（断口）。"""
    hy = hw if hy is None else hy
    cx, cy = hw * ch, hy * ch
    pts = [(hw, hy - cy), (hw - cx, hy), (-hw + cx, hy), (-hw, hy - cy), (-hw, -hy + cy), (-hw + cx, -hy),
           (hw - cx, -hy), (hw, -hy + cy)]
    return [Vector((x, y, z + (jit(i) if jit else 0.0))) for i, (x, y) in enumerate(pts)]


def sweep(name, pts, radii, mats, nu=20, per=4, up=(0, 0, 1), uv=(1.0, 1.0)):
    """带 UV 的扫掠管（开口两端）：沿 Catmull-Rom 细分路径放样圆截面，u 绕圈、v 为弧长（米）。
    工具包 tube 不写 UV，贴图材质（织物 / 雕花金）的管状件用它。"""
    P, rr = catmull(pts, radii, per) if per > 1 else ([Vector(p) for p in pts], list(radii))
    m = len(P)
    tan = [(P[min(i + 1, m - 1)] - P[max(i - 1, 0)]).normalized() for i in range(m)]
    upv = Vector(up)
    n0 = upv - tan[0] * upv.dot(tan[0])
    if n0.length < 1e-5:
        n0 = Vector((1, 0, 0)) - tan[0] * tan[0].x
    nor = [n0.normalized()]
    for i in range(1, m):
        nn = nor[-1] - tan[i] * nor[-1].dot(tan[i])
        nor.append(nn.normalized() if nn.length > 1e-6 else nor[-1])
    arc = [0.0]
    for i in range(1, m):
        arc.append(arc[-1] + (P[i] - P[i - 1]).length)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows = []
    for i in range(m):
        b = tan[i].cross(nor[i])
        rows.append([bm.verts.new(P[i] + (nor[i] * math.cos(TAU * j / nu) + b * math.sin(TAU * j / nu)) * rr[i])
                     for j in range(nu)])
    for i in range(m - 1):
        for j in range(nu):
            j2 = (j + 1) % nu
            f = bm.faces.new((rows[i][j], rows[i][j2], rows[i + 1][j2], rows[i + 1][j]))
            for loop, (uu, vv) in zip(f.loops, ((j, arc[i]), (j + 1, arc[i]), (j + 1, arc[i + 1]), (j, arc[i + 1]))):
                loop[uvl].uv = (uu / nu * uv[0], vv * uv[1])
    obj = bm_object(name, bm, mats)
    return orient(obj, lambda c: min(P, key=lambda q: (q - c).length_squared))


def frame3(n, up):
    """表面标架：法线 n、近似向上 up → (横轴 xa, 竖轴 ya, 法线 n)，满足 xa × ya = n。"""
    n = Vector(n).normalized()
    up = Vector(up)
    up = up - n * up.dot(n)
    if up.length < 1e-6:
        up = Vector((0, 0, 1)) - n * n.z
    up.normalize()
    xa = up.cross(n).normalized()
    return xa, up, n


def oriented_ellipsoid(name, center, radii, axes, mats, seg=16, rings=10):
    """局部轴 axes=(x, y, z) 下半径 radii 的椭球（用于掌心、护腕等斜向部件）。"""
    obj = ellipsoid(name, (0, 0, 0), radii, mats, seg, rings)
    m = Matrix((Vector(axes[0]), Vector(axes[1]), Vector(axes[2]))).transposed().to_4x4()
    return transform(obj, Matrix.Translation(Vector(center)) @ m)


def flat_ring(name, c, r0, r1, mats, seg=96, thick=0.01, uvfn=None, normal=(0, 0, 1), au=None, av=None):
    """平面环带：r0 内径、r1 外径，法线 normal；au/av 为环平面内两轴（a=0 在 av 方向，a 增大转向 au）。
    uvfn(u, v) 的 u 沿圆周 0→1、v 自内向外 0→1。"""
    c = Vector(c)
    nrm = Vector(normal).normalized()
    if au is None or av is None:
        xa, ya, _ = frame3(nrm, (0, 1, 0) if abs(nrm.z) > 0.9 else (0, 0, 1))
        au, av = xa, ya
    au, av = Vector(au).normalized(), Vector(av).normalized()

    def pt(u, v):
        a = u * TAU
        r = lerp(r0, r1, v)
        return c + au * (math.sin(a) * r) + av * (math.cos(a) * r)
    obj = surface(name, pt, seg, 2, mats, closed_u=True, uvfn=uvfn)
    orient(obj, lambda q: q - nrm)
    solidify(obj, thick, 0)
    return apply_all(obj)


# ===== 眼睛 =====
def almond(w, h, n=8, low=0.82, p=0.85):
    """杏仁形眼轮廓（x 横向 ±w，y 纵向 +h / -low*h），两角收尖。"""
    up = []
    for i in range(n + 1):
        t = -1 + 2 * i / n
        up.append((w * t, h * max(0.0, 1 - t * t) ** p))
    lo = []
    for i in range(n - 1, 0, -1):
        t = -1 + 2 * i / n
        lo.append((w * t, -h * low * max(0.0, 1 - t * t) ** p))
    return up + lo


def gem_lo(name, center, size, mat, stretch=(1.0, 0.6, 1.4)):
    """低面数宝石（8×6 椭球），代替 kit.gem（12×8），大量点缀时省面。"""
    s = size
    return ellipsoid(name, center, (s * stretch[0], s * stretch[1], s * stretch[2]), [mat], 8, 6)


def eye(ctx, M, name, c, nrm, up, w, h, spec, tilt=0.0, rim=None, pupil=0.15, lash=0.0, n=None, bulge=None,
        rim_mat="trim"):
    """发光杏仁眼：虹膜片（eye 发光）+ 竖瞳（pupil）+ 贵金属眼眶（trim 细管），可选外眼角金色眼线 lash。
    c 为表面中心、nrm 为外法线、up 为眼的竖直方向；tilt 绕法线旋转（π/2 为竖眼）。返回眼前表面中心点。"""
    n = n or (8 if h >= 0.03 else 6)
    xa, ya, nn = frame3(nrm, up)
    if tilt:
        rot = Matrix.Rotation(tilt, 3, nn)
        xa, ya = rot @ xa, rot @ ya
    c = Vector(c)
    d = max(0.004, h * 0.30)
    bl = bulge if bulge is not None else h * 0.35

    def bf(x, y):
        return bl * max(0.0, 1 - (x / w) ** 2) * max(0.0, 1 - (y / h) ** 2)
    ctx.part(plate(f"{name} iris", almond(w, h, n), d, [M["eye"]], origin=c, xaxis=xa, yaxis=ya, bulge=bf), spec)
    front = c + nn * (bl + d * 0.5)
    if pupil:
        ctx.part(plate(f"{name} pupil", almond(h * 0.86, w * pupil, 6, low=1.0), d * 0.7, [M["pupil"]],
                       origin=front, xaxis=ya, yaxis=-xa), spec)
    ring = [c + xa * (x * 1.07) + ya * (y * 1.10) + nn * (d * 0.45) for x, y in almond(w, h, n)]
    ctx.part(trim(f"{name} rim", ring, rim or max(0.0035, h * 0.11), M[rim_mat], closed=True, n=4), spec)
    if lash:
        for sd in (-1, 1):
            base = c + xa * (sd * w * 1.02) + nn * (d * 0.4)
            tip = base + xa * (sd * lash) - ya * (lash * 0.45) + nn * (d * 0.3)
            ctx.part(spike(f"{name} lash {sd}", base, tip, max(0.003, h * 0.16), [M[rim_mat]], sides=4,
                           up=tuple(nn)), spec)
    return front


def surf_frame(f, u, v, du=1e-3, dv=1e-3, out=None):
    """参数曲面 f(u, v) 上一点的位置、外法线与 -v 切向（向上）；out(p) 返回用于判定朝外的参考方向。"""
    p = f(u, v)
    pu = f(u + du, v) - f(u - du, v)
    pv = f(u, v + dv) - f(u, v - dv)
    n = pu.cross(pv).normalized()
    if out is not None and n.dot(out(p)) < 0:
        n = -n
    return p, n, -pv.normalized()


# ===== 动作工具 =====
def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


class Track:
    """关键参数轨道：keys=[(s, 值), ...]（s∈[0,1]），相邻关键之间平滑插值；值可为数或元组。"""

    def __init__(self, keys, shape=ease):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.shape = shape

    def __call__(self, s):
        ks = self.keys
        if s <= ks[0][0]:
            return ks[0][1]
        for (s0, v0), (s1, v1) in zip(ks, ks[1:]):
            if s <= s1:
                t = self.shape((s - s0) / max(1e-9, s1 - s0))
                if isinstance(v0, tuple):
                    return tuple(lerp(a, b, t) for a, b in zip(v0, v1))
                return lerp(v0, v1, t)
        return ks[-1][1]


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


def mix(a, b, t):
    """两个姿态逐项混合：旋转球面插值、浮点与向量线性插值。"""
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


def key_scale(rig, frames, fn):
    """在当前激活动作上为若干骨写缩放关键帧：fn(帧号) -> {骨名: (sx, sy, sz)}（骨局部轴，Y 沿骨长）。
    工具包 Rig.put_pose 只写旋转 / 位移，脉动缩放由这里补写。"""
    for f in frames:
        for name, sc in fn(f).items():
            pb = rig.obj.pose.bones[name]
            pb.scale = sc
            pb.keyframe_insert("scale", frame=f, group=name)


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
