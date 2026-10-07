"""裂隙猎犬 Rift Hound（mob-1）/ 裂隙头狼 Rift Alpha（elite-1）。

机械四足犬：深胸细腰的枪铁躯干分成前躯 Body / 后躯 Hips 两节（奔跑时脊柱屈伸），背脊一排骨白椎板与椎刺
（俯视最醒目），长楔形吻部顶着骨白颅甲、两侧各三点猩红感光器，上下颚内缘与獠牙发猩红光（咬合时张开），
后掠耳刺，数字行走的机械后腿，尾端一片骨白弯刃。
精英：放大 1.3 倍，镀金下颚、背脊椎刺换成高耸金刃、额前一对大弯角 + 脑后尖刺冠、加厚金边肩甲、胸口白红核心、
红色破鞍布；Attack 为低头直线冲锋。
骨架 14 节：Root / Body / Hips / Head / Jaw / Tail + 四腿各两节（Upper / Lower）。
"""

import math

from mathutils import Matrix, Vector

from chars._legion import SIDES, Legion, R, X, Z, cap_rim, plant, shift, steps

SIZE = 1.0
BODY_P = [(0, -0.06, 0.645), (0, 0.08, 0.655), (0, 0.24, 0.67), (0, 0.38, 0.685), (0, 0.47, 0.70)]
BODY_R = [(0.11, 0.095), (0.165, 0.135), (0.195, 0.165), (0.175, 0.155), (0.10, 0.10)]      # (竖直, 左右)
HIPS_P = [(0, -0.02, 0.645), (0, -0.18, 0.65), (0, -0.36, 0.66), (0, -0.50, 0.675)]
HIPS_R = [(0.10, 0.09), (0.13, 0.12), (0.14, 0.135), (0.09, 0.085)]
LEGS = ("FL", "FR", "HL", "HR")


def along(P, Rr, y):
    """沿 Y 走向的躯干管：按 y 插值得到 (中心 z, 竖直半径, 左右半径)。"""
    pts = sorted(zip(P, Rr), key=lambda pr: pr[0][1])
    for (p0, r0), (p1, r1) in zip(pts, pts[1:]):
        if p0[1] <= y <= p1[1]:
            t = (y - p0[1]) / (p1[1] - p0[1])
            return p0[2] + (p1[2] - p0[2]) * t, r0[0] + (r1[0] - r0[0]) * t, r0[1] + (r1[1] - r0[1]) * t
    (p, r) = pts[0] if y < pts[0][0][1] else pts[-1]
    return p[2], r[0], r[1]


def build(ctx, elite=False):
    L = Legion(ctx, elite, size=SIZE)
    E = elite
    J = L.joint
    for side, lb in SIDES:
        J(f"shoulder.F{lb}", (side * 0.13, 0.33, 0.68))
        J(f"elbow.F{lb}", (side * 0.14, 0.22, 0.40))
        J(f"paw.F{lb}", (side * 0.14, 0.30, 0.075))
        J(f"hip.H{lb}", (side * 0.12, -0.38, 0.66))
        J(f"knee.H{lb}", (side * 0.14, -0.24, 0.40))
        J(f"paw.H{lb}", (side * 0.14, -0.44, 0.075))
    # ----- 骨架 -----
    L.bone("Root", (0, 0, 0), (0, 0, 0.2))
    L.bone("Body", (0, -0.02, 0.66), (0, 0.40, 0.70), "Root")
    L.bone("Hips", (0, -0.02, 0.655), (0, -0.45, 0.67), "Body")
    L.bone("Head", (0, 0.40, 0.78), (0, 0.70, 0.86), "Body")
    L.bone("Jaw", (0, 0.575, 0.822), (0, 0.80, 0.795), "Head")
    L.bone("Tail", (0, -0.50, 0.70), (0, -0.80, 0.80), "Hips")
    for side, lb in SIDES:
        L.bone(f"Upper.F{lb}", L.J[f"shoulder.F{lb}"], L.J[f"elbow.F{lb}"], "Body")
        L.bone(f"Lower.F{lb}", L.J[f"elbow.F{lb}"], L.J[f"paw.F{lb}"], f"Upper.F{lb}")
        L.bone(f"Upper.H{lb}", L.J[f"hip.H{lb}"], L.J[f"knee.H{lb}"], "Hips")
        L.bone(f"Lower.H{lb}", L.J[f"knee.H{lb}"], L.J[f"paw.H{lb}"], f"Upper.H{lb}")
    L.translate["Body"] = "_bob"

    # ----- 躯干：深胸细腰 + 背脊椎板 / 椎刺 + 腹侧肋管 + 破鞍布 -----
    L.tube("chest", "Body", BODY_P, BODY_R, "armor", n=8, up=(0, 0, 1))
    L.tube("haunch", "Hips", HIPS_P, HIPS_R, "armor", n=8, up=(0, 0, 1))
    for k, y in enumerate((0.44, 0.33, 0.22, 0.11, 0.0, -0.11, -0.22, -0.33, -0.45)):
        bone = "Body" if y > -0.03 else "Hips"
        zc, rv, _ = along(BODY_P, BODY_R, y) if y > -0.03 else along(HIPS_P, HIPS_R, y)
        top = Vector((0, y, zc + rv - 0.005))
        L.box(f"vertebra plate {k}", bone, top, (0.085 - 0.02 * abs(y), 0.075, 0.035), "trim",
              taper=(0.6, 0.8))
        h = (0.07 if abs(y - 0.26) < 0.16 else 0.045) * (1.0 if not E else 2.4)
        if E:
            # 金脊刃：沿背线的后掠鳍刃（局部 x 朝后、y 朝上）
            fin = [(-0.035, -0.03), (0.03, -0.03), (0.035, 0.0), (0.065, h), (-0.015, h * 0.55), (-0.035, 0.0)]
            L.plate(f"spine blade {k}", bone, fin, 0.012, "trim", origin=top + Vector((0, 0, 0.01)), xaxis=(0, -1, 0),
                    yaxis=(0, 0.25, 1))
        else:
            L.spike(f"vertebra spike {k}", bone, top + Vector((0, 0.015, 0.012)), top + Vector((0, -0.04, h)), 0.022,
                    "trim", sides=3)
    for side, lb in SIDES:
        # 胸侧外露骨白肋（与空壳仆从的肋笼同源）
        for k, y in enumerate((0.26, 0.17, 0.08)):
            zc, rv, rl = along(BODY_P, BODY_R, y)
            pts = [Vector((side * rl * 1.08 * math.sin(a), y - 0.03 * (a - 0.3), zc + rv * 1.06 * math.cos(a)))
                   for a in (0.35, 1.0, 1.65, 2.3)]
            L.trim(f"flank rib {lb}{k}", "Body", pts, 0.012, "trim", n=4)
        L.cable(f"belly cable {lb}", "Body", [(side * 0.10, 0.34, 0.56), (side * 0.115, 0.10, 0.555),
                                              (side * 0.095, -0.12, 0.575)], 0.02, "armor", per=4, n=5)
        for k, (y, ln) in enumerate(((0.24, 0.24), (0.07, 0.20))):
            zc, rv, rl = along(BODY_P, BODY_R, y)
            L.strip(f"saddle rag {lb}{k}", "Body", (side * rl * 0.75, y, zc + rv * 0.72), (side * 0.45, 0, -1),
                    (0, 1, 0), 0.13, ln, jag=((0.7, 1.0, 0.8) if k else (1.0, 0.75, 0.9)), cup=0.012)
        # 前肩甲（挂 Body，腿在甲下摆动）
        fs = L.J[f"shoulder.F{lb}"]
        pr = (0.11, 0.13, 0.08) if not E else (0.13, 0.15, 0.095)
        L.cap(f"shoulder plate {lb}", "Body", fs + Vector((side * 0.035, 0.0, 0.05)), (side * 0.75, 0.05, 0.66), pr,
              "armor", theta=1.3, nu=7, nv=2, thick=0.012)
        if E:
            L.trim(f"shoulder rim {lb}", "Body", cap_rim(fs + Vector((side * 0.035, 0.0, 0.05)), (side * 0.75, 0.05, 0.66),
                                                        pr, 1.3, 7, grow=0.004), 0.008, "trim", n=3, closed=True)

    # ----- 头：楔形吻 + 骨白颅甲 + 三点感光 + 发光颚线 / 獠牙 + 耳刺 -----
    L.tube("neck", "Head", [(0, 0.38, 0.735), (0, 0.48, 0.81), (0, 0.565, 0.86)], [(0.10, 0.085), (0.085, 0.075),
                                                                                  (0.07, 0.065)], "armor", n=6)
    L.tube("skull", "Head", [(0, 0.53, 0.895), (0, 0.62, 0.893), (0, 0.72, 0.868), (0, 0.85, 0.845)],
           [(0.072, 0.075), (0.068, 0.07), (0.046, 0.05), (0.018, 0.024)], "armor", n=6)
    L.cap("brow mask", "Head", (0, 0.66, 0.895), (0, 0.12, 1), (0.070, 0.20, 0.048), "trim", theta=1.2, nu=8, nv=3,
          thick=0.01, shape=lambda p, th, ph: Vector((p.x * (1 - 0.55 * max(0.0, p.y / 0.20)), p.y, p.z)))
    for side, lb in SIDES:
        for k, (y, z) in enumerate(((0.585, 0.912), (0.625, 0.908), (0.665, 0.899))):
            w = 0.058 - 0.004 * k
            L.gem(f"sensor {lb}{k}", "Head", (side * w, y, z), 0.0125 if not E else 0.014, "glow",
                  stretch=(0.7, 1.0, 0.8), sides=4)
        L.spike(f"ear {lb}", "Head", (side * 0.05, 0.56, 0.93), (side * 0.10, 0.43, 1.10), 0.034, "armor", sides=4,
                flat=0.5, bend=(side * 0.01, 0.0, 0.02))
    U = [(-0.05, 0.585, 0.833), (-0.043, 0.70, 0.829), (0.0, 0.83, 0.832), (0.043, 0.70, 0.829), (0.05, 0.585, 0.833)]
    L.trim("upper gum", "Head", U, 0.0085, "glow", n=3)
    L.ell("maw", "Head", (0, 0.67, 0.822), (0.035, 0.12, 0.02), "glow", 6, 4)
    for side in (-1, 1):
        for k, y in enumerate((0.63, 0.70, 0.77)):
            x = side * (0.044 - 0.012 * k)
            L.spike(f"fang {side}{k}", "Head", (x, y, 0.835), (x, y + 0.01, 0.79 - 0.012 * (k == 0)), 0.009, "glow",
                    sides=3)
    # 下颚（挂 Jaw，咬合时张开）
    L.tube("jaw", "Jaw", [(0, 0.56, 0.815), (0, 0.66, 0.80), (0, 0.76, 0.795), (0, 0.825, 0.80)],
           [(0.035, 0.06), (0.03, 0.055), (0.022, 0.04), (0.012, 0.022)], "trim" if E else "armor", n=6)
    Lw = [(-0.05, 0.585, 0.823), (-0.04, 0.70, 0.818), (0.0, 0.81, 0.818), (0.04, 0.70, 0.818), (0.05, 0.585, 0.823)]
    L.trim("lower gum", "Jaw", Lw, 0.0075, "glow", n=3)
    for side in (-1, 1):
        for k, y in enumerate((0.66, 0.74)):
            x = side * (0.038 - 0.012 * k)
            L.spike(f"lower fang {side}{k}", "Jaw", (x, y, 0.815), (x, y - 0.005, 0.852), 0.008, "glow", sides=3)

    # ----- 腿 -----
    for side, lb in SIDES:
        fs, fe, fp = L.J[f"shoulder.F{lb}"], L.J[f"elbow.F{lb}"], L.J[f"paw.F{lb}"]
        L.tube(f"foreleg upper {lb}", f"Upper.F{lb}", [fs, fe], [0.08, 0.056], "armor", n=6)
        L.tube(f"foreleg lower {lb}", f"Lower.F{lb}", [fe, fp], [0.052, 0.036], "armor", n=6)
        L.wrap(f"forearm plate {lb}", f"Lower.F{lb}", fe.lerp(fp, 0.1), fe.lerp(fp, 0.75), 0.066, 0.052, (side * 0.3, 1, 0),
               "armor", arc=2.4, nu=4, nv=2, thick=0.012)
        L.spike(f"elbow spur {lb}", f"Lower.F{lb}", fe + Vector((0, -0.02, 0.0)), fe + Vector((0, -0.10, 0.03)), 0.025,
                "armor", sides=3)
        hh, hk, hp = L.J[f"hip.H{lb}"], L.J[f"knee.H{lb}"], L.J[f"paw.H{lb}"]
        hock = Vector((side * 0.14, -0.475, 0.22))
        L.tube(f"thigh {lb}", f"Upper.H{lb}", [hh, hk], [0.09, 0.058], "armor", n=6)
        L.wrap(f"thigh plate {lb}", f"Upper.H{lb}", hh.lerp(hk, 0.0), hh.lerp(hk, 0.8), 0.105, 0.075, (side, 0.3, 0.2),
               "armor", arc=2.3, nu=4, nv=2, thick=0.014)
        L.tube(f"shank {lb}", f"Lower.H{lb}", [hk, hock, hp], [0.055, 0.04, 0.034], "armor", n=6)
        L.spike(f"hock spur {lb}", f"Lower.H{lb}", hock, hock + Vector((0, -0.09, 0.05)), 0.024, "armor", sides=3)
        for tag, paw, bone in (("F", fp, f"Lower.F{lb}"), ("H", hp, f"Lower.H{lb}")):
            x, y = paw.x, paw.y
            L.tube(f"paw {tag}{lb}", bone, [(x, y - 0.05, 0.05), (x, y + 0.02, 0.046), (x, y + 0.10, 0.022)],
                   [(0.05, 0.045), (0.05, 0.05), (0.022, 0.034)], "armor", n=4, up=(0, 0, 1), twist=math.pi / 4)
            for dx in (-0.024, 0.0, 0.024):
                L.spike(f"claw {tag}{lb}{dx:+.3f}", bone, (x + dx, y + 0.085, 0.022), (x + dx * 1.25, y + 0.15, 0.004),
                        0.011, "armor", sides=3)

    # ----- 尾：三节枪铁尾椎 + 骨白弯刃 -----
    tp = [Vector(p) for p in ((0, -0.50, 0.70), (0, -0.615, 0.745), (0, -0.73, 0.785), (0, -0.845, 0.80))]
    for k in range(3):
        a, b = tp[k], tp[k + 1]
        L.tube(f"tail seg {k}", "Tail", [a + (b - a) * 0.05, b - (b - a) * 0.08], [0.042 - 0.007 * k, 0.034 - 0.006 * k],
               "armor", n=6)
    d = (tp[3] - tp[2]).normalized()
    w = Matrix.Rotation(math.radians(38), 3, d) @ Vector((1, 0, 0))
    k = 1.25 if E else 1.0
    blade = [(0, 0.030), (0.10, 0.052), (0.20, 0.040), (0.30, -0.012), (0.19, -0.022), (0.09, -0.032), (0.0, -0.022)]
    L.plate("tail blade", "Tail", [(x * k, y * k) for x, y in blade], 0.014, "trim", origin=tp[3] - d * 0.02, xaxis=d,
            yaxis=w)

    if E:
        build_alpha(L)
    return L.finalize()


def build_alpha(L):
    """精英升格件：额前大弯角、脑后尖刺冠、胸口白红核心。"""
    for side in (-1, 1):
        L.spike(f"horn {side}", "Head", (side * 0.05, 0.60, 0.925), (side * 0.19, 0.50, 1.10), 0.04, "trim", sides=4,
                bend=(side * 0.05, 0.08, 0.03))
    L.halo_crown("crown", "Head", (0, 0.50, 0.93), (0, -0.55, 0.84), 0.085, spikes=7, length=0.08, r=0.008, tilt=0.6)
    L.gem("chest core", "Body", (0, 0.49, 0.60), 0.04, "glow", stretch=(0.9, 0.6, 1.2), sides=4)
    L.ring("chest core rim", "Body", (0, 0.475, 0.60), (0, 1, -0.3), 0.05, 0.008, "trim", count=8, n=3, fwd=(0, 0, 1))


# ===== 动作 =====
REVIEW_POSE = ("Attack", 1)
FRONT_POLE = (0, -1, 0)


def leg_poles(label, side):
    return FRONT_POLE if label.startswith("F") else (side * 0.1, 1, 0)


def leg_rest(label, side):
    return FRONT_POLE if label.startswith("F") else (0, 1, 0)


def put_legs(rig, st, p, offs):
    """四腿 IK：offs 为 {腿: (dx, dy, dz)}（基础体型单位）。"""
    for lb in LEGS:
        side = -1 if lb.endswith("L") else 1
        plant(rig, st, p, lb, offs.get(lb, (0, 0, 0)), leg_poles(lb, side), "Upper", "Lower", "paw",
              leg_rest(lb, side))


def stand(rig, st):
    p = {}
    shift(p, st, z=-0.015)
    p["Jaw"] = R((X, -0.06))
    p["Tail"] = R((X, 0.05))
    put_legs(rig, st, p, {})
    return p


def move(rig, st, t):
    """旋转式疾驰：后腿先蹬、前腿后落，一个周期一次腾空；脊柱屈伸、头部稳定、尾刃甩动。"""
    p = {}
    shift(p, st, z=0.03 * math.sin(t + 0.6) - 0.01)
    p["Body"] = R((X, 0.07 * math.sin(t + 2.2)))
    p["Hips"] = R((X, -0.13 * math.sin(t + 0.3)))
    p["Head"] = R((X, -0.08 * math.sin(t + 2.2) - 0.04))
    p["Jaw"] = R((X, -(0.14 + 0.06 * math.sin(2 * t))))
    p["Tail"] = R((X, 0.12 + 0.10 * math.cos(t)), (Z, 0.18 * math.sin(t)))
    steps(rig, st, p, t, stride=0.52, lift=0.15, stance=0.40, heel=0.0, labels=LEGS, phases=(0.55, 0.47, 0.0, 0.08),
          upper="Upper", lower="Lower", key="paw", pole=leg_poles, rest_pole=leg_rest)
    return p


def pounce_key(rig, st, stage):
    """扑咬：1 伏低蓄力 / 2 腾扑张颚 / 3 落地咬合 / 0 回站。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=-0.12, y=-0.04)
        p["Body"] = R((X, -0.06))
        p["Hips"] = R((X, 0.10))
        p["Head"] = R((X, -0.12))
        p["Jaw"] = R((X, -0.10))
        p["Tail"] = R((X, -0.10))
        put_legs(rig, st, p, {"HL": (0, 0.06, 0), "HR": (0, 0.06, 0)})
    elif stage == 2:
        shift(p, st, z=0.20, y=0.30)
        p["Body"] = R((X, 0.20))
        p["Hips"] = R((X, -0.12))
        p["Head"] = R((X, -0.02))
        p["Jaw"] = R((X, -0.62))
        p["Tail"] = R((X, 0.35))
        put_legs(rig, st, p, {"FL": (0, 0.78, 0.34), "FR": (0, 0.70, 0.30), "HL": (0, -0.06, 0.08), "HR": (0, -0.02, 0.10)})
    else:
        shift(p, st, z=-0.04, y=0.42)
        p["Body"] = R((X, -0.10))
        p["Hips"] = R((X, 0.06))
        p["Head"] = R((X, -0.28))
        p["Jaw"] = R((X, -0.04))
        p["Tail"] = R((X, 0.20), (Z, 0.2))
        put_legs(rig, st, p, {"FL": (0, 0.40, 0.0), "FR": (0, 0.36, 0.0), "HL": (0, 0.10, 0.10), "HR": (0, 0.06, 0.12)})
    return p


def charge_key(rig, st, stage):
    """精英冲锋：1 伏低 / 2、3 低头顶角狂奔（前后腿交替大步）。"""
    if stage == 0:
        return stand(rig, st)
    if stage == 1:
        p = pounce_key(rig, st, 1)
        p["Head"] = R((X, -0.22))
        return p
    a = 1 if stage == 2 else -1
    p = {}
    shift(p, st, z=0.02 + 0.03 * a, y=0.10)
    p["Body"] = R((X, -0.05 + 0.05 * a))
    p["Hips"] = R((X, -0.12 * a))
    p["Head"] = R((X, -0.26))
    p["Jaw"] = R((X, -0.35))
    p["Tail"] = R((X, 0.30), (Z, 0.12 * a))
    put_legs(rig, st, p, {"FL": (0, 0.30 * a, 0.12 * (a < 0)), "FR": (0, 0.24 * a, 0.10 * (a < 0)),
                          "HL": (0, -0.28 * a, 0.12 * (a > 0)), "HR": (0, -0.22 * a, 0.10 * (a > 0))})
    return p


def animate(rig, st):
    rig.loop("Move", 16, lambda t: move(rig, st, t), step=1)
    if st["elite"]:
        k = [charge_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (5, k[1]), (8, k[2]), (11, k[3]), (14, k[2]), (17, k[3]), (22, k[0])])
    else:
        k = [pounce_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (6, k[1]), (10, k[2]), (13, k[3]), (18, k[0])])
