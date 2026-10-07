"""壁垒执事 Bulwark Deacon（mob-2）/ 壁垒院长 Bulwark Abbot（elite-2）。

宽厚的重甲构造体：桶形胸甲 + 胸前两条骨白圣带（执事的圣带）与骨白领环，巨大的层叠圆肩甲，陷在两肩之间的
小盔 + 骨白面甲上一道猩红横缝；左臂一面 1.6 m 的弧面塔盾，盾面刻猩红圣印（圆环 + 倒十字 + 三点），右手
下垂一柄翼缘钉锤。俯视时盾面是身前一道宽横杠，两肩是两团圆甲。
精英：放大 1.3 倍，金边塔盾、主教冠盔（双片尖拱冠 + 发光十字）、脑后尖刺光冠、肩甲金刺、钉锤换成弯首权杖；
Attack 为举杖 → 前指（配合五向扇形弹）。
"""

import math

from mathutils import Matrix, Vector

from chars._legion import SIDES, TAU, Legion, R, X, Y, Z, cap_rim, plant, section, shift, steps

SIZE = 1.045
TORSO_P = [(0, -0.01, 1.12), (0, 0.0, 1.30), (0, 0.02, 1.52), (0, 0.02, 1.74), (0, 0.01, 1.92), (0, 0.0, 2.0)]
TORSO_R = [(0.19, 0.25), (0.23, 0.31), (0.27, 0.37), (0.27, 0.39), (0.21, 0.30), (0.12, 0.16)]
SHIELD_C = Vector((-0.31, 0.60, 1.02))
SHIELD_N = Vector((-0.15, 1.0, 0.0)).normalized()


def shield_pt(u, v, grow=0.0, lift=0.0):
    """塔盾曲面：u∈[-1,1] 横向，v∈[0,1] 自上而下；上缘微拱、下端收尖，两侧向后弯。"""
    xa = Vector((1, 0.15, 0)).normalized()
    hw = 0.36 * (1 - max(0.0, (v - 0.72) / 0.28) ** 1.6 * 0.94) + grow
    top = 0.80 - 0.07 * u * u + grow
    bot = -0.46 - 0.32 * (1 - abs(u) ** 1.3) - grow
    z = top + (bot - top) * v
    x = u * hw
    return SHIELD_C + xa * x + Vector((0, 0, z)) + SHIELD_N * (lift - 0.085 * u * u)


def build(ctx, elite=False):
    L = Legion(ctx, elite, size=SIZE)
    E = elite
    J = L.joint
    for side, lb in SIDES:
        J(f"hip.{lb}", (side * 0.19, 0.0, 1.0))
        J(f"knee.{lb}", (side * 0.20, 0.13, 0.56))
        J(f"ankle.{lb}", (side * 0.21, 0.0, 0.12))
        J(f"shoulder.{lb}", (side * 0.40, 0.0, 1.82))
        J(f"elbow.{lb}", (side * 0.47, 0.05 if side < 0 else 0.03, 1.45))
    J("wrist.L", (-0.40, 0.40, 1.32))
    J("wrist.R", (0.45, 0.39, 1.36) if E else (0.45, 0.20, 1.12))
    L.bone("Root", (0, 0, 0), (0, 0, 0.3))
    L.bone("Pelvis", (0, 0, 0.98), (0, 0, 1.15), "Root")
    L.bone("Chest", (0, 0, 1.15), (0, 0.02, 1.95), "Pelvis")
    L.bone("Head", (0, 0.03, 1.95), (0, 0.06, 2.22), "Chest")
    for side, lb in SIDES:
        L.bone(f"UpperArm.{lb}", L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], "Chest")
        L.bone(f"Forearm.{lb}", L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"], f"UpperArm.{lb}")
        L.bone(f"Thigh.{lb}", L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], "Pelvis")
        L.bone(f"Shin.{lb}", L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"], f"Thigh.{lb}")
    L.translate["Pelvis"] = "_bob"

    # ----- 躯干：桶形胸甲 + 胸板 + 骨白圣带 / 领环 + 背部肋管 -----
    L.tube("torso", "Chest", TORSO_P, TORSO_R, "armor", n=8, up=(0, 1, 0))
    L.cap("breastplate", "Chest", (0, 0.10, 1.60), (0, 1, 0.12), (0.33, 0.30, 0.21), "armor", theta=1.05, nu=8, nv=2,
          thick=0.016, fwd=(0, 0, 1))
    for side in (-1, 1):
        pts = []
        for z in (1.90, 1.74, 1.56, 1.38, 1.22):
            cy, dep, wid = section(TORSO_P, TORSO_R, z)
            x = side * (0.13 - 0.05 * (1.90 - z))
            a = math.asin(max(-1.0, min(1.0, x / wid)))
            pts.append(Vector((x, cy + dep * math.cos(a) + (0.042 if 1.4 < z < 1.8 else 0.02), z)))
        L.tube(f"stole {side}", "Chest", pts, [(0.012, 0.045)] * len(pts), "trim", n=4, up=(0, 1, 0))
    L.ring("collar", "Chest", (0, 0.01, 1.93), (0, 0, 1), 0.25, 0.028, "trim", count=12, n=4, squash=0.78)
    for side, lb in SIDES:
        L.cable(f"back cable {lb}", "Chest", [(side * 0.12, -0.24, 1.38), (side * 0.16, -0.30, 1.62),
                                              (side * 0.10, -0.20, 1.95)], 0.035, "armor", per=3, n=5)

    # ----- 头：陷肩小盔 + 骨白面甲 + 猩红横缝（精英：主教冠） -----
    hc = Vector((0, 0.05, 2.06))
    L.cap("helm", "Head", hc, (0, -0.1, 1), (0.145, 0.165, 0.165), "armor", theta=1.75, nu=8, nv=3,
          phi=(0.75, TAU - 0.75), thick=0.014)
    L.cap("face plate", "Head", hc + Vector((0, 0.05, -0.02)), (0, 1, -0.05), (0.11, 0.13, 0.075), "trim", theta=1.2,
          nu=8, nv=2, fwd=(0, 0, 1), thick=0.012)
    L.tube("visor slit", "Head", [(-0.075, 0.172, 2.07), (0.0, 0.186, 2.072), (0.075, 0.172, 2.07)], [0.010, 0.013, 0.010],
           "glow", n=4)
    if not E:
        L.plate("helm crest", "Head", [(0.10, 0.10), (0.02, 0.21), (-0.12, 0.19), (-0.17, 0.08), (-0.05, 0.12)], 0.02,
                "trim", origin=hc + Vector((0, 0, 0.03)), xaxis=(0, 1, 0), yaxis=(0, 0, 1))

    # ----- 肩：层叠圆肩甲 + 骨白滚边 + 骨钉 -----
    for side, lb in SIDES:
        sh = L.J[f"shoulder.{lb}"]
        for k, (dz, r, th) in enumerate(((0.07, (0.23, 0.23, 0.17), 1.35), (-0.05, (0.21, 0.21, 0.13), 1.15))):
            c = sh + Vector((side * (0.03 + 0.03 * k), 0, dz))
            ax = (side * (0.5 + 0.25 * k), 0, 0.87)
            L.cap(f"pauldron {lb}{k}", "Chest", c, ax, r, "armor", theta=th, nu=8, nv=3 - k, thick=0.02)
            if k == 0:
                L.trim(f"pauldron rim {lb}", "Chest", cap_rim(c, ax, r, th, 8, grow=0.004), 0.012, "trim", n=3,
                       closed=True)
        top = sh + Vector((side * 0.03, 0, 0.07)) + Vector((side * 0.5, 0, 0.87)).normalized() * 0.17
        for k, dy in enumerate((-0.09, 0.0, 0.09)):
            b = top + Vector((side * 0.02 * (k != 1), dy, -0.01 * (k != 1)))
            L.spike(f"pauldron stud {lb}{k}", "Chest", b, b + Vector((side * 0.03, dy * 0.3, 0.10 if E else 0.06)),
                    0.03, "trim", sides=4)

    # ----- 手臂 -----
    for side, lb in SIDES:
        sh, el, wr = L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"]
        L.tube(f"upper arm {lb}", f"UpperArm.{lb}", [sh, el], [0.10, 0.08], "armor", n=6)
        L.tube(f"forearm {lb}", f"Forearm.{lb}", [el, wr], [0.085, 0.07], "armor", n=6)
        L.wrap(f"vambrace {lb}", f"Forearm.{lb}", el.lerp(wr, 0.1), el.lerp(wr, 0.8), 0.10, 0.09, (side, 0, -0.3),
               "armor", arc=2.6, nu=4, nv=2, thick=0.014)
        d = (wr - el).normalized()
        L.ell(f"gauntlet {lb}", f"Forearm.{lb}", wr + d * 0.05, (0.075, 0.085, 0.08), "armor", 6, 4)

    # ----- 塔盾（挂左前臂）：弧面盾体 + 骨白（精英金）盾缘 + 猩红圣印 + 四枚盾钉 -----
    L.surf("tower shield", "Forearm.L", lambda u, v: shield_pt(u * 2 - 1, v), 5, 6, "armor",
           ref=lambda q: q - SHIELD_N, thick=0.03, sharp=None)
    rim = [shield_pt(-1 + 2 * i / 6, 0, 0.012, 0.004) for i in range(7)]
    rim += [shield_pt(1, v / 5, 0.012, 0.004) for v in range(1, 6)]
    rim += [shield_pt(1 - 2 * i / 6, 1, 0.012, 0.004) for i in range(1, 6)]
    rim += [shield_pt(-1, 1 - v / 5, 0.012, 0.004) for v in range(0, 5)]
    L.trim("shield rim", "Forearm.L", rim, 0.016 if not E else 0.02, "trim", n=3, closed=True)
    sc = shield_pt(0, 0.34, 0, 0.022)
    xa = Vector((1, 0.15, 0)).normalized()
    L.ring("sigil ring", "Forearm.L", sc, SHIELD_N, 0.15, 0.011, "glow", count=10, n=3, fwd=(0, 0, 1))
    L.tube("sigil bar", "Forearm.L", [sc + Vector((0, 0, 0.26)), sc, sc + Vector((0, 0, -0.34))], [0.010, 0.014, 0.010],
           "glow", n=4)
    L.tube("sigil cross", "Forearm.L", [sc + xa * -0.11 + Vector((0, 0, -0.19)), sc + xa * 0.11 + Vector((0, 0, -0.19))],
           [0.010, 0.010], "glow", n=4)
    for k, a in enumerate((-0.6, 0.0, 0.6)):
        L.gem(f"sigil dot {k}", "Forearm.L", sc + xa * (math.sin(a) * 0.22) + Vector((0, 0, math.cos(a) * 0.22 + 0.02)),
              0.018, "glow", sides=4)
    for k, (u, v) in enumerate(((-0.72, 0.08), (0.72, 0.08), (-0.72, 0.70), (0.72, 0.70))):
        L.gem(f"shield boss {k}", "Forearm.L", shield_pt(u, v, 0, 0.02), 0.03, "trim", stretch=(1, 1, 0.8), sides=4)

    # ----- 右手武器：翼缘钉锤（精英换弯首权杖） -----
    wr = L.J["wrist.R"]
    if not E:
        top, head = wr + Vector((0.0, 0.05, 0.20)), wr + Vector((0.0, 0.18, -0.58))
        L.tube("mace haft", "Forearm.R", [top, head], [0.026, 0.026], "armor", n=5)
        for k, t in enumerate((0.05, 0.30)):
            L.ring(f"mace grip {k}", "Forearm.R", top.lerp(head, t), head - top, 0.032, 0.01, "armor", count=6, n=3)
        hd = (head - top).normalized()
        L.ell("mace core", "Forearm.R", head, (0.07, 0.07, 0.09), "armor", 6, 4)
        for k in range(4):
            a = TAU * k / 4 + 0.4
            rad = Matrix.Rotation(a, 3, hd) @ Vector((1, 0, 0))
            rad = (rad - hd * rad.dot(hd)).normalized()
            L.plate(f"mace flange {k}", "Forearm.R", [(-0.10, 0.0), (0.10, 0.0), (0.06, 0.07), (-0.07, 0.06)], 0.016,
                    "armor", origin=head + rad * 0.05, xaxis=hd, yaxis=rad)
        L.spike("mace tip", "Forearm.R", head + hd * 0.08, head + hd * 0.18, 0.03, "armor", sides=4)

    # ----- 骨盆：髋管 + 骨白腰带 + 前后长襟 + 侧腿甲 -----
    L.tube("hips", "Pelvis", [(0, 0, 0.92), (0, 0, 1.04), (0, 0, 1.17)], [(0.17, 0.24), (0.20, 0.28), (0.19, 0.26)],
           "armor", n=8, up=(0, 1, 0))
    L.ring("belt", "Pelvis", (0, 0, 1.10), (0, 0, 1), 0.29, 0.024, "armor", count=10, n=3, squash=0.72)
    L.strip("front tabard", "Pelvis", (0, 0.21, 1.08), (0, 0.22, -1), (1, 0, 0), 0.17, 0.62, jag=(0.8, 1.0, 0.85),
            cup=0.02, curl=0.03, nv=4, taper=0.1)
    L.strip("back tabard", "Pelvis", (0, -0.20, 1.10), (0, -0.25, -1), (1, 0, 0), 0.30, 0.80, jag=(0.75, 1.0, 0.7, 0.95, 0.8),
            cup=-0.03, curl=-0.04, nv=4, taper=0.1)
    for side, lb in SIDES:
        L.strip(f"side rag {lb}", "Pelvis", (side * 0.27, -0.03, 1.08), (side * 0.35, -0.1, -1), (0, 1, 0), 0.16, 0.42,
                jag=(0.7, 1.0, 0.8), cup=0.015)

    # ----- 腿：粗壮重腿 + 大护膝 + 宽靴 -----
    for side, lb in SIDES:
        hp, kn, an = L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"]
        th, sh = f"Thigh.{lb}", f"Shin.{lb}"
        L.tube(f"thigh {lb}", th, [hp, kn], [0.13, 0.10], "armor", n=6)
        L.wrap(f"cuisse {lb}", th, hp.lerp(kn, 0.05), hp.lerp(kn, 0.8), 0.15, 0.125, (side * 0.6, 0.8, 0), "armor",
               arc=2.6, nu=4, nv=2, thick=0.016)
        L.cap(f"knee {lb}", sh, kn + Vector((0, 0.05, 0.0)), (0, 1, 0.2), (0.105, 0.105, 0.08), "armor", theta=1.25,
              nu=7, nv=2, thick=0.014)
        L.gem(f"knee stud {lb}", sh, kn + Vector((0, 0.135, 0.0)), 0.028, "armor", stretch=(1, 0.8, 1), sides=4)
        L.tube(f"shin {lb}", sh, [kn, an], [0.10, 0.08], "armor", n=6)
        L.wrap(f"greave {lb}", sh, kn.lerp(an, 0.12), kn.lerp(an, 0.9), 0.12, 0.10, (0, 1, 0), "armor", arc=2.6, nu=4,
               nv=2, thick=0.014)
        x = an.x
        L.tube(f"sabaton {lb}", sh, [(x, -0.12, 0.085), (x, 0.03, 0.085), (x, 0.24, 0.05)],
               [(0.12, 0.085), (0.12, 0.10), (0.06, 0.065)], "armor", n=4, up=(0, 0, 1), twist=math.pi / 4)

    if E:
        build_abbot(L, hc)
    return L.finalize()


def build_abbot(L, hc):
    """精英升格件：主教冠（双片尖拱 + 金滚边 + 发光十字）、尖刺光冠、弯首权杖。"""
    arch = [(-0.13, 0.0), (0.13, 0.0), (0.12, 0.13), (0.07, 0.24), (0.0, 0.32), (-0.07, 0.24), (-0.12, 0.13)]
    for k, dy in enumerate((0.035, -0.035)):
        o = hc + Vector((0, dy, 0.10))
        ya = Vector((0, -dy * 2.2, 1)).normalized()
        L.plate(f"mitre {k}", "Head", arch, 0.024, "armor", origin=o, xaxis=(1, 0, 0), yaxis=ya)
        L.trim(f"mitre edge {k}", "Head", [o + Vector((x * 1.03, 0, 0)) + ya * (y * 1.03) for x, y in arch[1:] + arch[:1]],
               0.012, "trim", n=3)
    L.tube("mitre cross v", "Head", [hc + Vector((0, 0.074, 0.15)), hc + Vector((0, 0.07, 0.35))], [0.012, 0.012], "glow", n=4)
    L.tube("mitre cross h", "Head", [hc + Vector((-0.055, 0.073, 0.28)), hc + Vector((0.055, 0.073, 0.28))], [0.011, 0.011],
           "glow", n=4)
    L.ring("mitre band", "Head", hc + Vector((0, 0, 0.10)), (0, 0, 1), 0.16, 0.016, "trim", count=10, n=3, squash=0.95)
    L.halo_crown("halo crown", "Head", hc + Vector((0, -0.16, 0.16)), (0, -0.9, 0.44), 0.24, spikes=11, length=0.10,
                 r=0.010, tilt=0.3)
    # 弯首权杖（挂右前臂，竖握于身前）
    wr = L.J["wrist.R"]
    g = wr + Vector((0.0, 0.06, 0.0))
    base, top = g + Vector((0, 0.03, -1.18)), g + Vector((0, -0.04, 0.80))
    L.tube("crozier staff", "Forearm.R", [base, top], [0.022, 0.028], "armor", n=5)
    for k, t in enumerate((0.47, 0.56, 0.93)):
        L.ring(f"crozier band {k}", "Forearm.R", base.lerp(top, t), top - base, 0.036, 0.011, "trim", count=6, n=3)
    crook = [top + Vector((0, 0.03 * math.sin(a) + 0.0, 0.0)) + Vector((0, 0.13 * (1 - math.cos(a)), 0.15 * math.sin(a)))
             for a in (0.0, 0.8, 1.6, 2.4, 3.2, 3.9)]
    L.tube("crozier crook", "Forearm.R", crook, [0.03, 0.028, 0.026, 0.024, 0.02, 0.012], "trim", n=5)
    L.gem("crozier heart", "Forearm.R", top + Vector((0, 0.12, 0.13)), 0.045, "glow", stretch=(0.7, 0.7, 1.1), sides=4)


# ===== 动作 =====
REVIEW_POSE = ("Attack", 1)
UP = (0, 0, 1)


def stand(rig, st):
    p = {}
    shift(p, st, z=-0.02)
    for lb in ("L", "R"):
        plant(rig, st, p, lb, (0, 0, 0), ((-1 if lb == "L" else 1) * 0.1, 1, 0))
    return p


def move(rig, st, t):
    """重步前压：左右换重心的大幅侧倾、落脚一沉；盾稳稳护在身前，钉锤随步轻摆。"""
    p = {}
    shift(p, st, z=-0.035 + 0.025 * math.cos(2 * (t - 1.9)) - 0.012 * max(0.0, math.cos(2 * t)) ** 6)
    p["Pelvis"] = R((Z, -0.06 * math.cos(t)), (Y, 0.07 * math.sin(t)))
    p["Chest"] = R((Z, 0.08 * math.cos(t)), (Y, -0.05 * math.sin(t)), (X, -0.03))
    p["Head"] = R((Y, -0.02 * math.sin(t)))
    p["UpperArm.L"] = R((X, 0.04 * math.cos(t)))
    p["UpperArm.R"] = R((X, 0.16 * math.cos(t + math.pi)))
    p["Forearm.R"] = R((X, 0.06 + 0.05 * math.sin(t)))
    steps(rig, st, p, t, stride=0.40, lift=0.13, stance=0.62, width=0.01, pole_out=0.1)
    return p


def bash_key(rig, st, stage):
    """盾击：1 左肩后撤蓄力 / 2 跨步前撞 / 3 顶住。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=-0.06, y=-0.04)
        p["Pelvis"] = R((Z, 0.12))
        p["Chest"] = R((Z, 0.30), (X, 0.06))
        p["Head"] = R((Z, -0.20))
        rig.aim(p, "UpperArm.L", (-0.45, -0.30, -0.84))
        rig.aim(p, "Forearm.L", (0.10, 0.95, -0.15), up=UP, rest_up=UP)
        rig.aim(p, "UpperArm.R", (0.30, -0.30, -0.90))
        plant(rig, st, p, "L", (0, 0, 0), (-0.1, 1, 0))
        plant(rig, st, p, "R", (0, -0.05, 0), (0.1, 1, 0))
    else:
        k = 1.0 if stage == 2 else 0.8
        shift(p, st, z=-0.08, y=0.12 * k)
        p["Pelvis"] = R((Z, -0.16 * k), (X, 0.06))
        p["Chest"] = R((Z, -0.36 * k), (X, -0.14 * k))
        p["Head"] = R((Z, 0.3 * k), (X, 0.1))
        rig.aim(p, "UpperArm.L", (0.10, 0.85 * k, -0.50))
        rig.aim(p, "Forearm.L", (0.45, 0.88, -0.10), up=UP, rest_up=UP)
        rig.aim(p, "UpperArm.R", (0.30, -0.45, -0.85))
        plant(rig, st, p, "L", (0, 0.22, 0), (-0.1, 1, 0))
        plant(rig, st, p, "R", (0, -0.08, 0), (0.1, 1, 0))
    return p


def fan_key(rig, st, stage):
    """精英五向扇形弹：1 举杖蓄势（盾在前）/ 2 权杖前指、盾面圣印迎敌 / 3 保持。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    rig.aim(p, "UpperArm.L", (-0.25, 0.60, -0.76))
    if stage == 1:
        shift(p, st, z=-0.04)
        p["Chest"] = R((X, 0.08), (Z, 0.10))
        p["Head"] = R((X, 0.08))
        rig.aim(p, "Forearm.L", (0.10, 0.95, -0.10), up=UP, rest_up=UP)
        rig.aim(p, "UpperArm.R", (0.40, 0.20, 0.30))
        rig.aim(p, "Forearm.R", (0.05, 0.55, 0.84), up=(0, -1, 0.3), rest_up=UP)
        plant(rig, st, p, "L", (0, 0, 0), (-0.1, 1, 0))
        plant(rig, st, p, "R", (0, -0.04, 0), (0.1, 1, 0))
    else:
        k = 1.0 if stage == 2 else 0.85
        shift(p, st, z=-0.08, y=0.05)
        p["Chest"] = R((X, -0.12 * k), (Z, -0.08))
        p["Head"] = R((X, -0.05))
        rig.aim(p, "Forearm.L", (0.15, 1.0, 0.0), up=UP, rest_up=UP)
        # 权杖与前臂夹角固定约 104°：前臂前下指，杖身才会向前倾约 37° 指向敌阵
        rig.aim(p, "UpperArm.R", (0.30, 0.85, 0.20))
        rig.aim(p, "Forearm.R", (0.02, 0.63, -0.775), up=(0, 0.774 * k, 0.633 + 0.3 * (1 - k)), rest_up=UP)
        plant(rig, st, p, "L", (0, 0.10, 0), (-0.1, 1, 0))
        plant(rig, st, p, "R", (0, -0.06, 0), (0.1, 1, 0))
    return p


def animate(rig, st):
    rig.loop("Move", 24, lambda t: move(rig, st, t), step=1)
    if st["elite"]:
        k = [fan_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (8, k[1]), (12, k[2]), (17, k[3]), (24, k[0])])
    else:
        k = [bash_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (7, k[1]), (10, k[2]), (14, k[3]), (21, k[0])])
