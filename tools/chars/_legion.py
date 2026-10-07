"""零域军团（Null Legion）共享底座：调色板与材质、低模刚性部件、骨架登记、姿态 / 步态工具与统计。

约定与 tools/kit 一致：Blender Z 向上，正面朝 +Y，单位米；side=-1 / "L" 为 -X，side=+1 / "R" 为 +X。
杂兵 / 精英只用 ctx.attach 刚性挂骨（游戏内按部件矩阵实例化上百只）：不蒙皮、不用 Wrap / Panel 布料。
驱动按“骨 × 材质”合并网格节点（每个节点一次绘制调用），所以发光件、滚边件尽量集中在少数骨上。

几何一律按基础体型坐标建模；精英在 finalize() 里整体放大（网格、骨架、关节点同步），动作里的位移与
IK 目标乘 st["s"]，同一套动作函数对杂兵和精英通用。
"""

import math

import bmesh
from mathutils import Matrix, Vector

from kit.core import (TAU, apply_all, auto_smooth, bevel, bm_object, catmull, ellipsoid, finish, lerp, orient,
                      surface)
from kit.core import plate as kit_plate
from kit.motion import foot_track
from kit.rig import R, X, Y, Z  # noqa: F401  （给各类型模块统一从这里取）

ELITE_SCALE = 1.3
SIDES = ((-1, "L"), (1, "R"))


def lin(hexcode):
    """sRGB 十六进制色 → 线性色（Blender 材质与 glTF 因子都是线性值）。"""
    h = hexcode.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


# ===== 调色板（线性色） =====
ARMOR = (0.060, 0.064, 0.074)     # 炭灰枪铁
BONE = (0.70, 0.63, 0.50)         # 骨白陶瓷
RAGS = (0.042, 0.016, 0.012)      # 锈血破布（杂兵；也用作锈刃）
CAPE = (0.15, 0.011, 0.014)       # 破红披风（精英）
GOLD = (0.46, 0.29, 0.085)        # 暗金（精英镀金）
CRIMSON = lin("ff2438")           # 腐化猩红感光器
HOT = (1.0, 0.30, 0.24)           # 精英：更烫的白红核心
MINT = lin("8ee4b0")              # 香炉炮手弹幕色
VIOLET = lin("d995ff")            # 咒唱司铎弹幕色


def palette(ctx, elite=False, weapon=None):
    """建 ≤4 种材质，返回“角色 → 材质”表（armor / trim / cloth / glow / weapon）。
    近战：枪铁 + 骨白陶瓷（精英整体换暗金）+ 破布 + 猩红感光；远程：破布并入枪铁，第 4 种给武器弹幕色。"""
    ctx.mat("armor", "gunmetal armor", ARMOR, metal=0.8, rough=0.36)
    if elite:
        ctx.mat("trim", "tarnished gold", GOLD, metal=1.0, rough=0.32)
        ctx.mat("glow", "white-crimson core glow", tuple(0.6 * c for c in HOT), emit=HOT, strength=7.0)
    else:
        ctx.mat("trim", "bone ceramic", BONE, metal=0.0, rough=0.36, coat=0.4)
        ctx.mat("glow", "crimson sensor glow", tuple(0.35 * c for c in CRIMSON), emit=CRIMSON, strength=4.5)
    if weapon:
        suffix, col = weapon
        ctx.mat("weapon", suffix, tuple(0.4 * c for c in col), emit=col, strength=3.6)
    else:
        ctx.mat("cloth", "torn red cape cloth" if elite else "oxblood rag cloth", CAPE if elite else RAGS,
                rough=0.86, spec=0.3)
    M = dict(ctx.M)
    M.setdefault("cloth", M["armor"])
    M.setdefault("weapon", M["glow"])
    return M


# ===== 几何小工具 =====
def frame(axis, fwd=(0, 1, 0)):
    """局部标架（列向量）：z = axis，y = fwd 在垂直面上的投影，x = y × z。"""
    z = Vector(axis).normalized()
    f = Vector(fwd)
    y = f - z * f.dot(z)
    if y.length < 1e-6:
        y = z.orthogonal()
    y.normalize()
    return Matrix((y.cross(z), y, z)).transposed()


def pivot(center, m3):
    """绕 center 旋转 m3 的 4×4 矩阵（配合 Legion.xform 使用，点用 M @ Vector 变换）。"""
    c = Vector(center)
    return Matrix.Translation(c) @ m3.to_4x4() @ Matrix.Translation(-c)


def xf(obj, m3=None, center=(0, 0, 0), offset=(0, 0, 0)):
    """绕 center 旋转 m3 后再平移 offset（直接改网格数据，对象保持单位变换）。"""
    c = Vector(center)
    rot = m3.to_4x4() if m3 is not None else Matrix.Identity(4)
    obj.data.transform(Matrix.Translation(c + Vector(offset)) @ rot @ Matrix.Translation(-c))
    obj.data.update()
    return obj


def _tube(name, pts, rads, mat, n=6, up=(0, 0, 1), closed=False, cap=True, twist=0.0):
    """低模管 / 车削体：rads 为标量或 (沿 up 方向半径, 侧向半径)；首尾半径为 0 时收成尖点。"""
    pts = [Vector(p) for p in pts]
    rads = [(float(r), float(r)) if isinstance(r, (int, float)) else (float(r[0]), float(r[1])) for r in rads]
    m = len(pts)
    tang = []
    for i in range(m):
        d = (pts[(i + 1) % m] - pts[i - 1]) if closed else (pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)])
        tang.append(d.normalized())
    u = Vector(up)
    n0 = u - tang[0] * u.dot(tang[0])
    if n0.length < 1e-5:
        n0 = tang[0].orthogonal()
    nrm = [n0.normalized()]
    for i in range(1, m):
        v = nrm[-1] - tang[i] * nrm[-1].dot(tang[i])
        nrm.append(v.normalized() if v.length > 1e-6 else nrm[-1])
    bm = bmesh.new()
    rings = []
    for i in range(m):
        ru, rs = rads[i]
        if max(ru, rs) <= 1e-6 and not closed and i in (0, m - 1):
            rings.append([bm.verts.new(pts[i])])
            continue
        b = tang[i].cross(nrm[i])
        rings.append([bm.verts.new(pts[i] + nrm[i] * (math.cos(a) * ru) + b * (math.sin(a) * rs))
                      for a in (TAU * k / n + twist for k in range(n))])
    for i in range(m if closed else m - 1):
        ra, rb = rings[i], rings[(i + 1) % m]
        for k in range(n):
            k2 = (k + 1) % n
            try:
                if len(ra) == 1:
                    bm.faces.new((ra[0], rb[k2], rb[k]))
                elif len(rb) == 1:
                    bm.faces.new((ra[k], ra[k2], rb[0]))
                else:
                    bm.faces.new((ra[k], ra[k2], rb[k2], rb[k]))
            except ValueError:
                pass
    if cap and not closed:
        for ring in (rings[0], rings[-1]):
            if len(ring) > 2:
                try:
                    bm.faces.new(ring)
                except ValueError:
                    pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, [mat])


def _gem(name, c, size, mat, stretch=(1, 1, 1), sides=4, rot=None):
    """双锥宝石 / 感光点：2×sides 个三角面；rot 把局部 Z（尖端方向）转到目标方向。"""
    bm = bmesh.new()
    top = bm.verts.new((0, 0, size * stretch[2]))
    bot = bm.verts.new((0, 0, -size * stretch[2]))
    ring = [bm.verts.new((math.cos(a) * size * stretch[0], math.sin(a) * size * stretch[1], 0))
            for a in (TAU * k / sides for k in range(sides))]
    for k in range(sides):
        a, b = ring[k], ring[(k + 1) % sides]
        bm.faces.new((a, b, top))
        bm.faces.new((b, a, bot))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = bm_object(name, bm, [mat], smooth=False)
    rot4 = rot.to_4x4() if rot is not None else Matrix.Identity(4)
    obj.data.transform(Matrix.Translation(Vector(c)) @ rot4)
    return obj


def _box(name, c, size, mat, rot=None, taper=(1.0, 1.0), bev=0.0, shift=(0.0, 0.0)):
    """（可倒角的）楔形方块：taper 缩放顶面 x / y，shift 平移顶面，用来做靴头、甲片、棺盖。"""
    hx, hy, hz = (v / 2 for v in size)
    tx, ty = taper
    sx, sy = shift
    co = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
          (-hx * tx + sx, -hy * ty + sy, hz), (hx * tx + sx, -hy * ty + sy, hz),
          (hx * tx + sx, hy * ty + sy, hz), (-hx * tx + sx, hy * ty + sy, hz)]
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in co]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = bm_object(name, bm, [mat], smooth=False)
    if bev:
        bevel(obj, bev, 1, 30)
        apply_all(obj)
    rot4 = rot.to_4x4() if rot is not None else Matrix.Identity(4)
    obj.data.transform(Matrix.Translation(Vector(c)) @ rot4)
    return auto_smooth(obj, 30)


def _cap(name, c, axis, radii, mat, theta=1.3, nu=8, nv=3, phi=(0.0, TAU), fwd=(0, 1, 0), thick=0.0, shape=None):
    """球冠壳（肩甲、兜帽、面具、护膝、盾心）：局部 z = axis 为冠顶，theta 为张角，phi 可留开口。
    shape(local, th, ph) 可再改形；thick>0 时向内加厚并按角度拆硬边。"""
    F = frame(axis, fwd)
    c = Vector(c)
    full = abs(phi[1] - phi[0] - TAU) < 1e-6
    cols = nu if full else nu + 1

    def P(th, ph):
        loc = Vector((math.sin(th) * math.sin(ph) * radii[0], math.sin(th) * math.cos(ph) * radii[1],
                      math.cos(th) * radii[2]))
        if shape:
            loc = shape(loc, th, ph)
        return c + F @ loc
    bm = bmesh.new()
    pole = bm.verts.new(P(0.0, 0.0))
    rings = [[bm.verts.new(P(theta * k / nv, phi[0] + (phi[1] - phi[0]) * i / nu)) for i in range(cols)]
             for k in range(1, nv + 1)]
    for i in range(nu):
        i2 = (i + 1) % cols
        bm.faces.new((pole, rings[0][i], rings[0][i2]))
        for k in range(nv - 1):
            bm.faces.new((rings[k][i], rings[k + 1][i], rings[k + 1][i2], rings[k][i2]))
    obj = bm_object(name, bm, [mat])
    orient(obj, lambda q: c)
    if thick:
        finish(obj, thick, -1, 0)
        auto_smooth(obj, 50)
    return obj


def cap_rim(c, axis, radii, theta, count, phi=(0.0, TAU), fwd=(0, 1, 0), grow=0.0, shape=None):
    """球冠边缘的点列（给滚边用）。"""
    F = frame(axis, fwd)
    full = abs(phi[1] - phi[0] - TAU) < 1e-6
    pts = []
    for i in range(count if full else count + 1):
        ph = phi[0] + (phi[1] - phi[0]) * i / count
        loc = Vector((math.sin(theta) * math.sin(ph) * (radii[0] + grow), math.sin(theta) * math.cos(ph) * (radii[1] + grow),
                      math.cos(theta) * (radii[2] + grow)))
        if shape:
            loc = shape(loc, theta, ph)
        pts.append(Vector(c) + F @ loc)
    return pts


def _wrap(name, a, b, r0, r1, out, mat, arc=2.4, nu=5, nv=2, thick=0.008, bulge=0.0):
    """包在肢体段 a→b 外侧的弧形甲片（护腿、护臂、腿甲）：out 为甲片朝向，arc 为包角。"""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    o = Vector(out) - ax * Vector(out).dot(ax)
    o.normalize()
    sd = ax.cross(o)

    def f(u, v):
        ang = (u - 0.5) * arc
        r = lerp(r0, r1, v) + bulge * math.sin(math.pi * v)
        return a.lerp(b, v) + (o * math.cos(ang) + sd * math.sin(ang)) * r
    obj = surface(name, f, nu, nv, [mat])
    orient(obj, lambda q: a + ax * (q - a).dot(ax))
    if thick:
        finish(obj, thick, -1, 0)
        auto_smooth(obj, 50)
    return obj


def _strip(name, top, down, across, width, length, mat, cup=0.0, curl=0.0, jag=(0.8, 1.0, 0.7), nv=4,
           taper=0.25, sag=0.0):
    """破布条：单面薄片（材质双面渲染），jag 为各列长度比例 → 下缘长短不齐形成撕口。
    cup 横向微弧、curl 下端外卷（沿布面法线）、sag 中段下垂弯度。"""
    top, d = Vector(top), Vector(down).normalized()
    a = Vector(across)
    a = (a - d * a.dot(d)).normalized()
    nrm = a.cross(d)
    ncol = len(jag)

    def f(u, v):
        ci = u * (ncol - 1)
        i0 = min(int(ci), ncol - 2)
        L = length * lerp(jag[i0], jag[i0 + 1], ci - i0)
        c = (u - 0.5) * 2
        off = cup * (1 - c * c) + curl * v * v + sag * math.sin(math.pi * v)
        return top + a * ((u - 0.5) * width * (1 - taper * v)) + d * (v * L) + nrm * off
    return surface(name, f, ncol, nv, [mat])


def _ring(name, c, normal, radius, r, mat, count=10, n=4, fwd=(0, 1, 0), squash=1.0):
    """闭合细环（滚边环、光环、链环）。squash 压扁局部 y 方向。"""
    F = frame(normal, fwd)
    pts = [Vector(c) + F @ Vector((math.sin(a) * radius, math.cos(a) * radius * squash, 0))
           for a in (TAU * k / count for k in range(count))]
    return _tube(name, pts, [r] * count, mat, n=n, closed=True, up=Vector(normal))


def _spike(name, base, tip, r, mat, sides=4, bend=None, flat=1.0, up=(0, 0, 1), twist=0.0):
    """尖刺 / 爪 / 角：bend 为中点偏移向量（弯角），flat 压扁截面。"""
    b, t = Vector(base), Vector(tip)
    if bend is not None:
        pts, rads = [b, b.lerp(t, 0.5) + Vector(bend), t], [(r * flat, r), (r * 0.55 * flat, r * 0.55), 0.0]
    else:
        pts, rads = [b, t], [(r * flat, r), 0.0]
    return _tube(name, pts, rads, mat, n=sides, up=up, twist=twist)


def _cable(name, pts, r, mat, per=4, n=5, rib=0.68):
    """肋状线管：沿平滑路径交替粗细，形成一节节的肋。"""
    P, _ = catmull(pts, [r] * len(pts), per)
    return _tube(name, P, [r if i % 2 == 0 else r * rib for i in range(len(P))], mat, n=n)


def section(pts, rads, z):
    """按高度 z 在一条竖直躯干管的点列 / 半径表里插值，返回 (中心 y, 前后半径, 左右半径)。"""
    i = 0
    while i < len(pts) - 2 and z > pts[i + 1][2]:
        i += 1
    z0, z1 = pts[i][2], pts[i + 1][2]
    t = max(0.0, min(1.0, (z - z0) / (z1 - z0)))
    return (lerp(pts[i][1], pts[i + 1][1], t), lerp(rads[i][0], rads[i + 1][0], t),
            lerp(rads[i][1], rads[i + 1][1], t))


def resample(pts, step):
    """把折线按弧长等距重采样，返回 [(点, 切向), ...]。"""
    pts = [Vector(p) for p in pts]
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum((b - a).length for a, b in segs)
    count = max(1, int(total / step))
    out = []
    for k in range(count + 1):
        d = total * k / count
        for a, b in segs:
            L = (b - a).length
            if d <= L + 1e-9:
                out.append((a.lerp(b, d / max(L, 1e-9)), (b - a).normalized()))
                break
            d -= L
    return out


class Legion:
    """单个军团单位的构建器：材质角色、刚性挂骨部件、骨骼与关节点登记，finalize 时统一放大并统计。"""

    def __init__(self, ctx, elite=False, weapon=None, size=1.0):
        self.ctx = ctx
        self.elite = elite
        self.scale = size * (ELITE_SCALE if elite else 1.0)
        self.M = palette(ctx, elite, weapon)
        self.bones, self.J, self.translate, self.parts = [], {}, {}, []
        self.xform = None      # 非空时，之后登记的部件先经此 4×4 变换（例如把直立建模的躯干整体压成佝偻）

    # ----- 登记 -----
    def m(self, mat):
        return self.M[mat] if isinstance(mat, str) else mat

    def put(self, obj, bone, sharp=None):
        if self.xform is not None:
            obj.data.transform(self.xform)
            obj.data.update()
        if sharp:
            auto_smooth(obj, sharp)
        self.ctx.attach(obj, bone)
        self.parts.append((obj, bone))
        return obj

    def nm(self, name):
        return f"{self.ctx.title} {name}"

    def bone(self, name, head, tail, parent=None):
        self.bones.append((name, Vector(head), Vector(tail), parent))
        return name

    def joint(self, key, p):
        self.J[key] = Vector(p)
        return self.J[key]

    # ----- 部件（全部立即挂骨） -----
    def tube(self, name, bone, pts, rads, mat, n=6, up=(0, 0, 1), closed=False, cap=True, twist=0.0, sharp=None):
        return self.put(_tube(self.nm(name), pts, rads, self.m(mat), n, up, closed, cap, twist), bone, sharp)

    def trim(self, name, bone, pts, r, mat="trim", n=4, closed=False):
        return self.put(_tube(self.nm(name), pts, [r] * len(pts), self.m(mat), n, closed=closed), bone)

    def ell(self, name, bone, c, r, mat, seg=8, rings=6, rot=None, sharp=None):
        obj = ellipsoid(self.nm(name), c, r, [self.m(mat)], seg, rings)
        if rot is not None:
            xf(obj, rot, c)
        return self.put(obj, bone, sharp)

    def gem(self, name, bone, c, size, mat="glow", stretch=(1, 1, 1), sides=4, rot=None):
        return self.put(_gem(self.nm(name), c, size, self.m(mat), stretch, sides, rot), bone)

    def box(self, name, bone, c, size, mat, rot=None, taper=(1.0, 1.0), bev=0.0, shift=(0.0, 0.0)):
        return self.put(_box(self.nm(name), c, size, self.m(mat), rot, taper, bev, shift), bone)

    def plate(self, name, bone, outline, depth, mat, origin, xaxis, yaxis, bulge=None, bev=0.0):
        obj = kit_plate(self.nm(name), outline, depth, [self.m(mat)], origin=origin, xaxis=xaxis, yaxis=yaxis,
                        bulge=bulge, bev=bev, bev_seg=1)
        return self.put(obj, bone)

    def cap(self, name, bone, c, axis, radii, mat, sharp=None, **kw):
        return self.put(_cap(self.nm(name), c, axis, radii, self.m(mat), **kw), bone, sharp)

    def wrap(self, name, bone, a, b, r0, r1, out, mat, **kw):
        return self.put(_wrap(self.nm(name), a, b, r0, r1, out, self.m(mat), **kw), bone)

    def strip(self, name, bone, top, down, across, width, length, mat="cloth", **kw):
        return self.put(_strip(self.nm(name), top, down, across, width, length, self.m(mat), **kw), bone)

    def ring(self, name, bone, c, normal, radius, r, mat, **kw):
        return self.put(_ring(self.nm(name), c, normal, radius, r, self.m(mat), **kw), bone)

    def spike(self, name, bone, base, tip, r, mat, **kw):
        return self.put(_spike(self.nm(name), base, tip, r, self.m(mat), **kw), bone)

    def cable(self, name, bone, pts, r, mat="armor", **kw):
        return self.put(_cable(self.nm(name), pts, r, self.m(mat), **kw), bone)

    def surf(self, name, bone, fn, nu, nv, mat, thick=0.0, ref=None, sharp=None):
        obj = surface(self.nm(name), fn, nu, nv, [self.m(mat)])
        if ref is not None:
            orient(obj, ref)
        if thick:
            finish(obj, thick, -1, 0)
            auto_smooth(obj, 50)
        return self.put(obj, bone, sharp)

    def chain(self, name, bone, pts, mat, link=0.06, wire=0.010, width=0.034, phase=0, lean=False):
        """链条：沿折线等距摆链环，相邻环互相垂直。lean=True 用菱形 4 点环（每环 24 面，长链省面）。"""
        samples = resample(pts, link * 0.78)
        ref = Vector((0, 0, 1))
        objs = []
        for k, (c, d) in enumerate(samples):
            side = d.cross(ref)
            if side.length < 1e-4:
                side = d.orthogonal()
            side.normalize()
            if (k + phase) % 2:
                side = d.cross(side).normalized()
            hx, hw = link * 0.5, width * 0.5
            if lean:
                loop = [c + d * hx, c + side * hw, c - d * hx, c - side * hw]
            else:
                loop = [c + d * hx, c + d * hx * 0.5 + side * hw, c - d * hx * 0.5 + side * hw, c - d * hx,
                        c - d * hx * 0.5 - side * hw, c + d * hx * 0.5 - side * hw]
            objs.append(self.put(_tube(self.nm(f"{name} link {k}"), loop, [wire] * len(loop), self.m(mat), n=3,
                                       closed=True, up=d.cross(side)), bone))
        return objs

    def eye(self, name, bone, c, fwd, size, socket=None, mat="glow"):
        """单只感光眼：扁圆发光体 + 可选枪铁眼眶环。"""
        rot = frame(fwd, (0, 0, 1))
        self.ell(name, bone, c, (size, size, size * 0.55), mat, 6, 4, rot=rot)
        if socket:
            self.ring(f"{name} socket", bone, Vector(c) - Vector(fwd).normalized() * size * 0.2, fwd,
                      size * 1.25, size * 0.28, socket, count=6, n=3, fwd=(0, 0, 1))

    def halo_crown(self, name, bone, c, normal, radius, spikes=8, length=0.10, r=0.010, fwd=(0, 1, 0), tilt=0.0,
                   mat="trim"):
        """精英尖刺光冠：细金环 + 放射尖刺（尖刺沿环面外撇，俯视时读作一圈星芒）。"""
        n = Vector(normal).normalized()
        F = frame(n, fwd)
        self.ring(f"{name} ring", bone, c, n, radius, r, mat, count=14, n=4, fwd=fwd)
        for k in range(spikes):
            a = TAU * k / spikes
            radial = F @ Vector((math.sin(a), math.cos(a), 0))
            base = Vector(c) + radial * radius
            L = length * (1.25 if k % 2 == 0 else 0.8)
            tip = base + (radial * math.cos(tilt) + n * math.sin(tilt)) * L
            self.spike(f"{name} spike {k}", bone, base, tip, r * 2.2, mat, sides=3, up=n)

    # ----- 收尾 -----
    def finalize(self, **extra):
        """整体放大（精英）、统计三角面 / 网格节点 / 包围盒，返回给 skeleton / animate 的状态。"""
        s = self.scale
        if abs(s - 1.0) > 1e-6:
            S = Matrix.Scale(s, 4)
            for obj, _ in self.parts:
                obj.data.transform(S)
                obj.data.update()
        bones = [(n, h * s, t * s, p) for n, h, t, p in self.bones]
        J = {k: v * s for k, v in self.J.items()}
        per = {}
        lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
        for obj, b in self.parts:
            key = (b, obj.data.materials[0].name.replace(self.ctx.title + " ", ""))
            per[key] = per.get(key, 0) + sum(len(p.vertices) - 2 for p in obj.data.polygons)
            for v in obj.data.vertices:
                lo = Vector(map(min, lo, v.co))
                hi = Vector(map(max, hi, v.co))
        tris = sum(per.values())
        print(f"LEGION {self.ctx.id}: tris {tris}, nodes {len(per)}, bones {len(bones)}, "
              f"height {hi.z - lo.z:.3f} (z {lo.z:.3f}..{hi.z:.3f}), x {lo.x:.2f}..{hi.x:.2f}, y {lo.y:.2f}..{hi.y:.2f}")
        for (b, mname), n in sorted(per.items(), key=lambda kv: -kv[1]):
            print(f"  NODE {b:>12} | {mname:<28} {n}")
        st = {"bones": bones, "J": J, "s": s, "translate": dict(self.translate), "elite": self.elite,
              "tris": tris, "nodes": len(per), "height": hi.z - lo.z}
        st.update(extra)
        return st


# ===== 骨架与姿态工具 =====
def skeleton(rig, st):
    for name, h, t, par in st["bones"]:
        rig.bone(name, h, t, par)
    rig.translate.update(st["translate"])


def shift(pose, st, z=0.0, y=0.0, x=0.0, key="_bob"):
    """根部位移通道（按体型缩放）：float 只写 Z，否则写向量。"""
    s = st["s"]
    pose[key] = Vector((x * s, y * s, z * s))


def plant(rig, st, pose, label, off=(0, 0, 0), pole=(0, 1, 0), upper="Thigh", lower="Shin", key="ankle",
          rest_pole=(0, 1, 0)):
    """两段腿 IK：脚踝目标 = 静止脚踝 + off（基础体型单位），pole 为膝盖朝向。
    rest_pole 为静止骨架里关节弯向（犬前腿肘朝后时给 -Y，否则挂在骨上的爪会被整体翻转 180°）。"""
    target = st["J"][f"{key}.{label}"] + Vector(off) * st["s"]
    rig.ik2(pose, f"{upper}.{label}", f"{lower}.{label}", target, Vector(pole), rest_pole=Vector(rest_pole))


def steps(rig, st, pose, t, stride, lift, stance=0.58, width=0.0, pole_out=0.12, heel=0.02, labels=("L", "R"),
          phases=(0.0, 0.5), upper="Thigh", lower="Shin", key="ankle", pole=None, rest_pole=None, strides=None):
    """步态：kit.motion.foot_track 给出脚踝轨迹（前段支撑向后滑、后段摆动前送），IK 求腿。
    pole / rest_pole 可为函数 (label, side) -> 向量，strides 可按腿给不同步幅。"""
    for i, (label, ph) in enumerate(zip(labels, phases)):
        side = -1 if label.endswith("L") else 1
        p = (t / TAU + ph) % 1.0
        dy, dz, _ = foot_track(p, strides[i] if strides else stride, lift, stance, heel)
        pl = pole(label, side) if pole else (side * pole_out, 1, 0)
        rp = rest_pole(label, side) if rest_pole else (0, 1, 0)
        plant(rig, st, pose, label, (side * width, dy, dz), pl, upper, lower, key, rp)


def swing_x(a):
    return R((X, a))
