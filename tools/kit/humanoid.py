"""角色工具包 · 人形：比例关键点、标准骨架、紧身衣与四肢、手、常用盔甲部件。

所有部件都通过 ctx.part(对象, 蒙皮规格) 登记；左右件用 side=-1/+1、label="L"/"R"（+X 为 R 侧）。
"""

import math

import bmesh
from mathutils import Matrix, Vector

from kit.core import (TAU, apply_all, bm_object, chain, clamp, ellipsoid, finish, gem, interp, invdist, lerp,
                      orient, radial, rigid, rotate, smoothstep, solidify, subsurf, surface, transform, trim,
                      tube, axis_ref)
from kit.rig import Y, Z

SIDES = ((-1, "L"), (1, "R"))


class Body:
    """英雄比例（约 8 头身）：height 为头顶高度，hover 为整体离地高度（漂浮角色）。"""

    BASE = [(0.94, (0.135, 0.100, -0.005)), (1.02, (0.160, 0.112, -0.008)), (1.12, (0.150, 0.104, -0.004)),
            (1.22, (0.128, 0.092, 0.000)), (1.30, (0.132, 0.094, 0.004)), (1.40, (0.150, 0.108, 0.006)),
            (1.48, (0.165, 0.116, 0.006)), (1.56, (0.178, 0.114, 0.004)), (1.62, (0.182, 0.104, 0.000)),
            (1.655, (0.150, 0.088, -0.004)), (1.68, (0.090, 0.066, -0.004)), (1.70, (0.060, 0.054, 0.000))]

    def __init__(self, height=2.0, shoulder=0.20, bulk=1.0, chest=1.0, waist=1.0, hips=1.0, limb=1.0,
                 hover=0.0, arm_out=0.62, arm_fwd=0.10, elbow_bend=0.22, female=False, stance=1.0):
        s = self.s = height / 2.0
        self.H, self.hover, self.female, self.limb = height, hover, female, limb
        z = self.z = lambda k: hover + k * s
        self.head_top, self.chin, self.neck_base = z(2.0), z(1.75), z(1.665)
        self.shoulder_z, self.chest_z, self.waist_z = z(1.615), z(1.49), z(1.26)
        self.pelvis_z, self.hip_z, self.knee_z, self.ankle_z = z(1.14), z(1.02), z(0.55), z(0.095)
        self.head_c = Vector((0, 0.012 * s, z(1.875)))
        self.head_r = (0.085 * s, 0.098 * s, 0.125 * s)
        self.sw = shoulder * s
        widen = shoulder / 0.20
        self.torso = []
        for kz, (rx, ry, yo) in self.BASE:
            up = smoothstep(1.30, 1.56, kz)
            low = 1 - smoothstep(1.12, 1.30, kz)
            wx = lerp(1.0, widen * chest, up) * lerp(1.0, hips, low) * lerp(1.0, waist, math.exp(-((kz - 1.24) / 0.08) ** 2))
            self.torso.append((z(kz), (rx * s * wx * (1 if kz < 1.66 else 1), ry * s * bulk, yo * s)))
        self.arms, self.hands, self.legs = {}, {}, {}
        for side, label in SIDES:
            S = Vector((side * self.sw, -0.005 * s, self.shoulder_z - 0.012 * s))
            d1 = Vector((side * math.sin(arm_out), arm_fwd * 0.5, -math.cos(arm_out))).normalized()
            E = S + d1 * 0.335 * s
            d2 = rotate(d1, Vector((1, 0, 0)), -elbow_bend)
            d2 = (d2 + Vector((0, arm_fwd, 0))).normalized()
            W = E + d2 * 0.29 * s
            self.arms[label] = {"shoulder": S, "elbow": E, "wrist": W, "inner": Vector((side * 0.10 * s, -0.004 * s, self.shoulder_z - 0.004 * s))}
            hx = side * 0.095 * s * hips * stance
            hip = Vector((hx, -0.004 * s, self.hip_z))
            knee = Vector((side * 0.100 * s * stance, 0.012 * s, self.knee_z))
            ankle = Vector((side * 0.104 * s * stance, -0.018 * s, self.ankle_z))
            ball = Vector((side * 0.108 * s * stance, 0.125 * s, hover + 0.028 * s))
            toe = Vector((side * 0.110 * s * stance, 0.215 * s, hover + 0.016 * s))
            self.legs[label] = {"hip": hip, "knee": knee, "ankle": ankle, "ball": ball, "toe": toe}

    def torso_r(self, z):
        return interp(self.torso, z)

    def torso_point(self, a, z, grow=0.0):
        """a=0 为正前方（+Y），a 增大转向 +X；grow 为沿截面外扩量。"""
        rx, ry, yo = self.torso_r(z)
        x = (rx + grow) * math.sin(a)
        y = yo + (ry + grow) * math.cos(a)
        if self.female:
            front = max(0.0, math.cos(a))
            bust = 0.024 * self.s * (math.exp(-((x - 0.068 * self.s) ** 2) / 0.0011) +
                                     math.exp(-((x + 0.068 * self.s) ** 2) / 0.0011))
            y += bust * front ** 2 * math.exp(-((z - self.z(1.50)) ** 2) / 0.0016)
        return Vector((x, y, z))

    def front_angle(self, x, z, grow):
        rx = self.torso_r(z)[0] + grow
        return math.asin(clamp(x / rx, -0.999, 0.999))

    def on_torso(self, x, z, grow, back=False):
        a = self.front_angle(x, z, grow)
        return self.torso_point(math.pi - a if back else a, z, grow)


# ===== 骨架 =====
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


def add_skeleton(rig, B, fingers=True, legs=True):
    s = B.s
    rig.bone("Root", (0, 0, 0), (0, 0, 0.2))
    rig.bone("Hover", (0, 0, 0.2), (0, 0, 0.45), "Root")
    rig.bone("Pelvis", (0, 0, B.pelvis_z), (0, 0, B.waist_z + 0.02 * s), "Hover", roll=Y)
    rig.bone("Spine", (0, 0, B.waist_z + 0.02 * s), (0, 0, B.chest_z - 0.02 * s), "Pelvis", roll=Y)
    rig.bone("Chest", (0, 0, B.chest_z - 0.02 * s), (0, 0, B.neck_base), "Spine", roll=Y)
    rig.bone("Neck", (0, 0.004 * s, B.neck_base), (0, 0.010 * s, B.chin + 0.03 * s), "Chest", roll=Y)
    rig.bone("Head", (0, 0.010 * s, B.chin + 0.03 * s), (0, 0.010 * s, B.head_top), "Neck", roll=Y)
    for side, label in SIDES:
        a = B.arms[label]
        rig.bone(f"UpperArm.{label}", a["shoulder"], a["elbow"], "Chest", roll=Y)
        rig.bone(f"Forearm.{label}", a["elbow"], a["wrist"], f"UpperArm.{label}", roll=Y)
        h = B.hands.get(label)
        if h:
            rig.bone(f"Hand.{label}", h["wrist"], h["knuckle"], f"Forearm.{label}", roll=h["n"])
            if fingers:
                for name, (base, tip) in h["fingers"].items():
                    rig.bone(f"{name}.{label}", base, tip, f"Hand.{label}", roll=h["n"])
        else:
            w = a["wrist"]
            rig.bone(f"Hand.{label}", w, w + (a["wrist"] - a["elbow"]).normalized() * 0.09 * s,
                     f"Forearm.{label}", roll=Y)
        if legs:
            L = B.legs[label]
            rig.bone(f"Thigh.{label}", L["hip"], L["knee"], "Pelvis", roll=Y)
            rig.bone(f"Shin.{label}", L["knee"], L["ankle"], f"Thigh.{label}", roll=Y)
            rig.bone(f"Foot.{label}", L["ankle"], L["ball"], f"Shin.{label}", roll=Z)
            rig.bone(f"Toe.{label}", L["ball"], L["toe"], f"Foot.{label}", roll=Z)
    rig.translate["Hover"] = "_hover"


# ===== 紧身衣与四肢 =====
def suit_torso(ctx, B, mat, z0=None, z1=None, grow=0.0, nu=40, nv=30):
    z0 = z0 if z0 is not None else B.torso[-1][0]
    z1 = z1 if z1 is not None else B.torso[0][0]
    body = surface(f"{ctx.title} torso", lambda u, v: B.torso_point(u * TAU, lerp(z0, z1, v), grow), nu, nv,
                   [mat], closed_u=True)
    orient(body, axis_ref)
    subsurf(body, 1)
    ctx.part(apply_all(body), invdist(["Pelvis", "Spine", "Chest", "Neck"]))
    neck = tube(f"{ctx.title} neck", [(0, 0, B.neck_base - 0.02 * B.s), (0, 0.006 * B.s, B.chin),
                                      (0, 0.012 * B.s, B.chin + 0.06 * B.s)],
                [0.052 * B.s, 0.044 * B.s, 0.042 * B.s], [mat], n=16)
    ctx.part(neck, invdist(["Chest", "Neck", "Head"]))
    return body


def suit_arm(ctx, B, side, label, mat, r=(0.046, 0.050, 0.043, 0.036, 0.028)):
    a = B.arms[label]
    s = B.s * B.limb
    mid = (a["shoulder"] + a["elbow"]) / 2
    arm = tube(f"{ctx.title} arm {label}", [a["inner"], a["shoulder"], mid, a["elbow"], a["wrist"]],
               [x * s for x in r], [mat], n=18)
    ctx.part(arm, chain([f"UpperArm.{label}", f"Forearm.{label}", f"Hand.{label}"], "Chest", 0.05))
    return arm


def suit_leg(ctx, B, side, label, mat, r=(0.088, 0.080, 0.062, 0.060, 0.050, 0.040)):
    L = B.legs[label]
    s = B.s * B.limb
    hip, knee, ankle = L["hip"], L["knee"], L["ankle"]
    top = hip + Vector((0, 0, 0.05 * B.s))
    pts = [top, hip.lerp(knee, 0.35), knee, knee.lerp(ankle, 0.3), knee.lerp(ankle, 0.7), ankle]
    leg = tube(f"{ctx.title} leg {label}", pts, [x * s for x in r], [mat], n=20)
    ctx.part(leg, chain([f"Thigh.{label}", f"Shin.{label}", f"Foot.{label}"], "Pelvis", 0.06))
    return leg


def hand(ctx, B, side, label, mat, glow=None, scale=1.12, finger_r=0.0096, claw=None):
    """尼克斯同款铠甲手：掌心朝前、拇指朝外；claw=(材质, 长度) 时指尖加利爪。"""
    a = B.arms[label]
    s = B.s
    wrist, elbow = a["wrist"], a["elbow"]
    f = ((wrist - elbow).normalized() + Vector((0, 0, -0.55))).normalized()
    n = Vector((0, 1, 0.15))
    n = (n - f * n.dot(f)).normalized()
    s0 = f.cross(n).normalized()
    flipped = s0.x * side < 0
    sv = -s0 if flipped else s0
    knuckle = wrist + f * 0.085 * s
    objs = []
    palm = tube(f"{ctx.title} palm {label}", [wrist - f * 0.004 * s, wrist + f * 0.045 * s, knuckle],
                [0.024 * s, 0.030 * s, 0.029 * s], [mat], n=14, fy=0.46, up=tuple(sv))
    objs.append((palm, rigid(f"Hand.{label}")))
    fingers = {}
    spec = (("Index", 0.020, 0.30, (0.042, 0.026, 0.020)), ("Middle", 0.007, 0.10, (0.046, 0.029, 0.021)),
            ("Ring", -0.007, -0.10, (0.043, 0.027, 0.020)), ("Pinky", -0.020, -0.30, (0.034, 0.021, 0.017)))
    for name, offset, spread, lengths in spec:
        base = knuckle + sv * offset * s - f * 0.004 * s
        d = rotate(f, n, spread if flipped else -spread)
        pts = [base]
        for length, curl in zip(lengths, (0.12, 0.18, 0.16)):
            d = rotate(d, d.cross(n), curl)
            pts.append(pts[-1] + d * length * s)
        fr = finger_r * s
        objs.append((tube(f"{ctx.title} finger {label} {name}", pts, [fr, fr * 0.92, fr * 0.77, 0.0], [mat],
                          n=8, per=4), chain([f"{name}.{label}"], f"Hand.{label}", 0.012)))
        if claw:
            objs.append((tube(f"{ctx.title} claw {label} {name}", [pts[-2], pts[-1] + d * claw[1] * s],
                              [fr * 0.8, 0.0], [claw[0]], n=6, per=1), rigid(f"{name}.{label}")))
        fingers[name] = (base, pts[-1])
    tbase = wrist + f * 0.018 * s + sv * 0.020 * s + n * 0.004 * s
    d = (f * 0.55 + sv * 0.75 + n * 0.35).normalized()
    pts = [tbase]
    for length, curl in zip((0.030, 0.024, 0.019), (0.10, 0.16, 0.14)):
        d = rotate(d, d.cross(n), curl)
        pts.append(pts[-1] + d * length * s)
    objs.append((tube(f"{ctx.title} thumb {label}", pts, [0.0094 * s, 0.0084 * s, 0.0070 * s, 0.0], [mat],
                      n=8, per=4), chain([f"Thumb.{label}"], f"Hand.{label}", 0.012)))
    fingers["Thumb"] = (tbase, pts[-1])
    # 指节护片：手背一排小甲片
    for i, off in enumerate((0.020, 0.007, -0.007, -0.020)):
        c = knuckle + sv * off * s - n * 0.012 * s - f * 0.006 * s
        objs.append((ellipsoid(f"{ctx.title} knuckle {label} {i}", c, (0.008 * s, 0.006 * s, 0.009 * s), [mat], 10, 6),
                     rigid(f"Hand.{label}")))
    if glow:
        disc = ellipsoid(f"{ctx.title} palm glow {label}", (0, 0, 0), (0.013 * s, 0.013 * s, 0.0022 * s), [glow], 16, 8)
        rot = n.to_track_quat("Z", "Y").to_matrix().to_4x4()
        transform(disc, Matrix.Translation(wrist + f * 0.046 * s + n * 0.0135 * s) @ rot)
        objs.append((disc, rigid(f"Hand.{label}")))
    sc = Matrix.Translation(wrist) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-wrist)
    for obj, spec_ in objs:
        transform(obj, sc)
        ctx.part(obj, spec_)
    B.hands[label] = {"wrist": wrist, "knuckle": sc @ knuckle, "f": f, "n": n, "s": sv,
                      "fingers": {k: (sc @ p, sc @ q) for k, (p, q) in fingers.items()}}
    return B.hands[label]


# ===== 盔甲部件 =====
def shell(ctx, B, name, zt, zb, grow, mat, spec, a0=0.0, a1=TAU, thick=0.008, nu=72, nv=24, sub=1,
          trims=None, shape=None):
    """贴合躯干的甲壳：zt/zb 为高度常数或 f(a)，shape(a, z) 返回额外外扩；trims=(材质, 半径)。"""
    full = abs(a1 - a0 - TAU) < 1e-6
    zt_f = zt if callable(zt) else (lambda a: zt)
    zb_f = zb if callable(zb) else (lambda a: zb)

    def pt(u, v):
        a = a0 + u * (a1 - a0)
        z = lerp(zt_f(a), zb_f(a), v)
        g = grow + (shape(a, z) if shape else 0.0)
        return B.torso_point(a, z, g)
    obj = surface(name, pt, nu, nv, [mat], closed_u=full)
    orient(obj, axis_ref)
    ctx.part(finish(obj, thick, 1, sub), spec)
    if trims:
        for v in (0.0, 1.0):
            n = nu + 24
            pts = [radial(pt(i / (n if full else n - 1), v), trims[1] * 2.6) for i in range(n)]
            ctx.part(trim(f"{name} trim {v}", pts, trims[1], trims[0], closed=full), spec)
        if not full:
            for u in (0.0, 1.0):
                pts = [radial(pt(u, j / 30), trims[1] * 2.6) for j in range(31)]
                ctx.part(trim(f"{name} side {u}", pts, trims[1], trims[0]), spec)
    return pt


def pauldron(ctx, B, side, label, mat, trim_mat=None, gem_mat=None, lames=3, radius=0.11, spread=1.32,
             rise=1.18, tilt=0.30, spire=0.0, spire_at=-0.30, spire_dir=(0.28, -0.22, 1.0),
             theta=((0.08, 0.92), (0.70, 1.30), (1.10, 1.66)), shrink=(1.0, 0.955, 0.90), thick=0.007,
             trim_r=0.0026, spec=None, offset=(0, 0, 0), ridge=0.0):
    """分层肩甲（尼克斯同款泛化）：lames 片弧形甲叠放，首片可带尖角 spire。"""
    s = B.s
    shoulder = B.arms[label]["shoulder"] + Vector((side * 0.0, 0.001, 0.02 * s)) + Vector(offset) * s
    spec = spec or rigid(("Chest", 0.35), (f"UpperArm.{label}", 0.65))

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
        lame = surface(f"{ctx.title} pauldron {label}{k}", lambda u, v, k=k: lp(k, 2 * u - 1, v), 30, 9, [mat])
        orient(lame, lambda c: shoulder)
        ctx.part(finish(lame, thick, 0, 1), spec)
        if trim_mat:
            edge = [lp(k, 2 * i / 48 - 1, 1.0) for i in range(49)]
            edge = [p + (p - shoulder).normalized() * 0.004 * s for p in edge]
            ctx.part(trim(f"{ctx.title} pauldron {label}{k} trim", edge, trim_r * s, trim_mat), spec)
    if gem_mat:
        g = lp(0, 0.25, 0.55)
        g += (g - shoulder).normalized() * 0.006 * s
        ctx.part(ellipsoid(f"{ctx.title} pauldron gem {label}", g, (0.0075 * s,) * 3, [gem_mat], 12, 8), spec)
    return lp, shoulder


def limb_frame(a, b, out):
    axis = (b - a).normalized()
    o = Vector(out)
    o = (o - axis * o.dot(axis)).normalized()
    return axis, o, axis.cross(o)


def limb_plate(ctx, name, a, b, r0, r1, mat, spec, out, arc=1.75, v0=0.0, v1=1.0, bulge=0.0, ridge=0.0,
               flare0=0.0, flare1=0.0, thick=0.005, nu=26, nv=12, trim_mat=None, trim_r=0.0022, closed=False,
               sub=1, rims=(0, 1)):
    """包裹肢体段 a→b 的弧形甲片；out 为甲片中心朝向，arc 为半张角（π 且 closed=True 为整圈）。"""
    axis, o, w = limb_frame(a, b, out)

    def pt(u, v):
        th = (2 * u - 1) * arc if not closed else u * TAU
        c = a.lerp(b, lerp(v0, v1, v))
        r = (lerp(r0, r1, v) + bulge * math.sin(v * math.pi) + ridge * math.exp(-(th / 0.28) ** 2)
             + flare0 * (1 - smoothstep(0.0, 0.18, v)) + flare1 * smoothstep(0.82, 1.0, v))
        return c + (o * math.cos(th) + w * math.sin(th)) * r

    def on_axis(c):
        return a + (b - a) * clamp((c - a).dot(b - a) / (b - a).length_squared)
    obj = surface(name, pt, nu, nv, [mat], closed_u=closed)
    orient(obj, on_axis)
    ctx.part(finish(obj, thick, 1, sub), spec)
    if trim_mat:
        for v in rims:
            n = nu + 8
            pts = [pt(i / (n if closed else n - 1), v) for i in range(n)]
            pts = [p + (p - on_axis(p)).normalized() * thick * 1.2 for p in pts]
            ctx.part(trim(f"{name} rim {v}", pts, trim_r, trim_mat, closed=closed), spec)
    return pt


def rerebrace(ctx, B, side, label, mat, trim_mat=None, arc=1.75, r=(0.059, 0.049), **kw):
    a = B.arms[label]
    s = B.s * B.limb
    return limb_plate(ctx, f"{ctx.title} rerebrace {label}", a["shoulder"], a["elbow"], r[0] * s, r[1] * s, mat,
                      rigid(f"UpperArm.{label}"), Vector((side, 0, 0.6)), arc=arc, v0=0.22, v1=0.86,
                      bulge=0.005 * s, trim_mat=trim_mat, **kw)


def vambrace(ctx, B, side, label, mat, trim_mat=None, inlay=None, r=(0.043, 0.047), spur=None, **kw):
    """护臂：整圈锥管，腕口外扩；inlay 外侧发光线，spur=(材质, 长度) 肘尖刺。"""
    a = B.arms[label]
    s = B.s * B.limb
    e, w = a["elbow"], a["wrist"]
    fdir = (w - e).normalized()
    a0, a1 = e + fdir * 0.03 * B.s, w - fdir * 0.012 * B.s
    out = Vector((side, -0.35, 0.25))
    pt = limb_plate(ctx, f"{ctx.title} vambrace {label}", a0, a1, r[0] * s, r[1] * s, mat, rigid(f"Forearm.{label}"),
                    out, closed=True, flare1=0.006 * s, trim_mat=trim_mat, nu=24, nv=10, **kw)
    axis, o, wv = limb_frame(a0, a1, out)
    if inlay:
        line = [a0.lerp(a1, t) + o * (lerp(r[0], r[1], t) * s + 0.0035 * B.s) for t in [i / 12 for i in range(13)]]
        ctx.part(trim(f"{ctx.title} vambrace inlay {label}", line, 0.0017 * B.s, inlay), rigid(f"Forearm.{label}"))
    if spur:
        ctx.part(tube(f"{ctx.title} elbow spur {label}", [e + o * 0.02 * B.s - fdir * 0.005 * B.s,
                                                         e + o * spur[1] * B.s - fdir * 0.045 * B.s],
                      [0.016 * B.s, 0.0], [spur[0]], n=8, per=1), rigid(f"Forearm.{label}"))
    return pt


def cuisse(ctx, B, side, label, mat, trim_mat=None, arc=2.1, r=(0.098, 0.082), **kw):
    L = B.legs[label]
    s = B.s * B.limb
    return limb_plate(ctx, f"{ctx.title} cuisse {label}", L["hip"], L["knee"], r[0] * s, r[1] * s, mat,
                      rigid(f"Thigh.{label}"), Vector((side * 0.55, 1, 0)), arc=arc, v0=0.10, v1=0.88,
                      bulge=0.006 * s, ridge=0.006 * s, trim_mat=trim_mat, **kw)


def greave(ctx, B, side, label, mat, trim_mat=None, r=(0.068, 0.052), **kw):
    L = B.legs[label]
    s = B.s * B.limb
    return limb_plate(ctx, f"{ctx.title} greave {label}", L["knee"], L["ankle"], r[0] * s, r[1] * s, mat,
                      rigid(f"Shin.{label}"), Vector((0, 1, 0)), closed=True, v0=0.10, v1=0.93,
                      bulge=0.010 * s, ridge=0.006 * s, flare1=0.008 * s, trim_mat=trim_mat, nu=28, **kw)


def poleyn(ctx, B, side, label, mat, trim_mat=None, gem_mat=None, size=0.062, wing=0.05):
    """护膝：前凸甲杯 + 外侧扇形翼。"""
    L = B.legs[label]
    s = B.s
    knee = L["knee"] + Vector((0, 0.045 * s, 0.005 * s))
    cup = ellipsoid(f"{ctx.title} poleyn {label}", knee, (size * s * 0.9, size * s * 0.62, size * s), [mat], 20, 14)
    ctx.part(cup, rigid(("Thigh." + label, 0.5), ("Shin." + label, 0.5)))
    fan = []
    for k in range(5):
        t = k / 4 - 0.5
        fan.append(knee + Vector((side * (0.035 + wing * 0.8) * s, (0.01 - 0.02 * abs(t)) * s, t * 0.06 * s)))
    wing_obj = tube(f"{ctx.title} poleyn wing {label}", [knee + Vector((side * 0.03 * s, 0.01 * s, 0.03 * s)),
                                                       knee + Vector((side * (0.03 + wing) * s, -0.01 * s, 0.0)),
                                                       knee + Vector((side * 0.03 * s, 0.01 * s, -0.03 * s))],
                    [0.012 * s, 0.018 * s, 0.012 * s], [mat], n=6, fx=0.35, up=(side, 0, 0))
    ctx.part(wing_obj, rigid(("Thigh." + label, 0.5), ("Shin." + label, 0.5)))
    if trim_mat:
        rim = [knee + Vector((math.sin(t) * size * s * 0.92, 0.012 * s, math.cos(t) * size * s * 1.02))
               for t in [i / 40 * TAU for i in range(40)]]
        ctx.part(trim(f"{ctx.title} poleyn rim {label}", rim, 0.0024 * s, trim_mat, closed=True),
                 rigid(("Thigh." + label, 0.5), ("Shin." + label, 0.5)))
    if gem_mat:
        ctx.part(gem(f"{ctx.title} poleyn gem {label}", knee + Vector((0, size * s * 0.6, 0)), 0.008 * s, gem_mat,
                     (1, 0.6, 1.2)), rigid(("Thigh." + label, 0.5), ("Shin." + label, 0.5)))
    return knee


def sabaton(ctx, B, side, label, mat, trim_mat=None, width=0.052, height=0.06, lames=4, toe_mat=None):
    """铁靴：脚背分段甲片 + 尖头，脚跟挂 Foot、趾尖挂 Toe。"""
    L = B.legs[label]
    s = B.s
    ankle, ball, toe = L["ankle"], L["ball"], L["toe"]
    heel = Vector((ankle.x, ankle.y - 0.05 * s, B.hover + 0.02 * s))
    sole = tube(f"{ctx.title} boot {label}", [heel, Vector((ankle.x, ankle.y + 0.02 * s, B.hover + 0.045 * s)),
                                              ball + Vector((0, 0, 0.012 * s)), toe],
                [width * s * 0.9, width * s, width * s * 0.9, width * s * 0.35], [mat], n=16, fx=1.0, fy=0.62,
                up=(0, 0, 1))
    ctx.part(sole, chain([f"Foot.{label}", f"Toe.{label}"], f"Shin.{label}", 0.03))
    for k in range(lames):
        t = k / lames
        c = ankle.lerp(ball, 0.15 + t * 0.85) + Vector((0, 0, (height * (1 - t) + 0.02) * s * 0.55))
        seg = ellipsoid(f"{ctx.title} sabaton lame {label}{k}", c, (width * s * 1.02, 0.028 * s, 0.022 * s * (1 - t * 0.3)),
                        [mat], 16, 8)
        ctx.part(seg, rigid(f"Foot.{label}"))
        if trim_mat:
            rim = [c + Vector((math.sin(a) * width * s * 1.04, 0.02 * s, math.cos(a) * 0.02 * s)) for a in
                   [(-1.4 + i * 2.8 / 16) for i in range(17)]]
            ctx.part(trim(f"{ctx.title} sabaton rim {label}{k}", rim, 0.0018 * s, trim_mat), rigid(f"Foot.{label}"))
    cap = ellipsoid(f"{ctx.title} toe cap {label}", ball.lerp(toe, 0.55) + Vector((0, 0, 0.018 * s)),
                    (width * s * 0.8, 0.055 * s, 0.022 * s), [toe_mat or mat], 16, 8)
    ctx.part(cap, rigid(f"Toe.{label}"))
    return heel


def gorget(ctx, B, mat, trim_mat=None, layers=((1.645, 1.695, 0.090, 0.070), (1.685, 1.735, 0.072, 0.056))):
    s = B.s
    for k, (z0, z1, r0, r1) in enumerate(layers):
        z0, z1 = B.z(z0), B.z(z1)

        def g(u, v, z0=z0, z1=z1, r0=r0 * s, r1=r1 * s):
            a = u * TAU
            z = lerp(z0, z1, v) - 0.018 * s * max(0.0, math.cos(a)) ** 4 * (1 - v)
            r = lerp(r0, r1, v)
            return Vector((r * math.sin(a), 0.004 * s + 0.006 * s * v + r * math.cos(a) * 0.92, z))
        obj = surface(f"{ctx.title} gorget {k}", g, 48, 6, [mat], closed_u=True)
        orient(obj, axis_ref)
        ctx.part(finish(obj, 0.004 * s, 1, 1), invdist(["Chest", "Neck"]))
        if trim_mat:
            rim = [g(i / 48, 1.0) for i in range(48)]
            rim = [p + Vector((p.x, p.y - 0.004 * s, 0)).normalized() * 0.005 * s for p in rim]
            ctx.part(trim(f"{ctx.title} gorget {k} trim", rim, 0.0022 * s, trim_mat, closed=True),
                     invdist(["Chest", "Neck"]))


def torso_inlay(ctx, B, paths, grow, mat, spec, radius=0.0019, via_mat=None, via=0.0045, mirror=True, back=False):
    """躯干表面的电路嵌线：paths 为 [(x, z), ...] 折线（右半侧），自动镜像并贴合表面。"""
    s = B.s
    sides = (-1, 1) if mirror else (1,)
    for sd in sides:
        for i, path in enumerate(paths):
            pts = []
            for (x0, z0), (x1, z1) in zip(path, path[1:]):
                for k in range(8):
                    t = k / 8
                    x, z = lerp(x0, x1, t) * sd * s, B.z(lerp(z0, z1, t))
                    pts.append(B.on_torso(x, z, grow, back))
            x, z = path[-1][0] * sd * s, B.z(path[-1][1])
            end = B.on_torso(x, z, grow, back)
            pts.append(end)
            ctx.part(trim(f"{ctx.title} inlay {'b' if back else 'f'}{sd}{i}", pts, radius * s, mat), spec)
            if via_mat:
                ctx.part(ellipsoid(f"{ctx.title} via {'b' if back else 'f'}{sd}{i}", end, (via * s,) * 3,
                                   [via_mat], 12, 8), spec)
