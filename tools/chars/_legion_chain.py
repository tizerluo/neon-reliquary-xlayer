"""锁链苦修者 Chain Penitent（mob-5）/ 锁链殉道者 Chain Martyr（elite-5）。

佝偻的缠链壮汉：背上一口房形圣物箱（枪铁箱体 + 骨白包角 + 人字顶 + 一圈铁刺 + 背面猩红圣窗），一条斜挎胸前的
锁链把箱子捆在身上；低垂的头缩在两肩之间，布套兜帽下骨白面具三点竖排猩红感光（像泪痕）；巨臂缠链环，
右拳拖一条链枷（链与刺球挂在独立的 Flail 骨上，挥击时滞后甩动）。俯视：背上一只尖顶带刺的箱子。
精英：放大 1.3 倍，圣物箱换成燃烧的金栅圣骸笼（白红火芯 + 火舌）、链条全部镀金、尖刺光冠、金边肩甲；
Attack 为抱拳蓄势 → 双臂猛张、笼火暴燃（配五向扇形弹）。骨架 13 节。
"""

import math

from mathutils import Matrix, Vector

from chars._legion import SIDES, TAU, Legion, R, X, Y, Z, cap_rim, pivot, plant, section, shift, steps

SIZE = 0.95
TORSO_P = [(0, -0.01, 0.94), (0, 0.0, 1.08), (0, 0.01, 1.28), (0, 0.01, 1.48), (0, 0.02, 1.62)]
TORSO_R = [(0.17, 0.21), (0.19, 0.26), (0.25, 0.35), (0.24, 0.37), (0.13, 0.20)]
WAIST = Vector((0, -0.01, 0.98))
HUNCH = 0.45
BOX_C = Vector((0, -0.40, 1.50))
BOX_S = (0.56, 0.28, 0.66)


def build_box(L, E):
    """背负圣物箱（直立坐标，调用前已设 L.xform = 前压矩阵）。精英换成燃烧的金栅圣骸笼。"""
    c, (w, d, h) = BOX_C, BOX_S
    zt = c.z + h / 2
    if not E:
        L.box("reliquary", "Chest", c, BOX_S, "armor", bev=0.012)
        for sx in (-1, 1):
            for sy in (-1, 1):
                L.trim(f"box corner {sx}{sy}", "Chest", [Vector((sx * w / 2, c.y + sy * d / 2, c.z - h / 2)),
                                                          Vector((sx * w / 2, c.y + sy * d / 2, zt))], 0.022, "trim", n=4)
        L.trim("box band", "Chest", [Vector((x * w / 2 * 1.02, c.y + y * d / 2 * 1.04, c.z - 0.12)) for x, y in
                                     ((-1, -1), (1, -1), (1, 1), (-1, 1))], 0.016, "trim", n=3, closed=True)
        # 背面圣窗：竖槽发光 + 枪铁十字栅
        wc = Vector((0, c.y - d / 2 - 0.004, c.z + 0.04))
        L.box("relic window", "Chest", wc, (0.16, 0.012, 0.34), "glow")
        L.box("window bar v", "Chest", wc + Vector((0, -0.01, 0)), (0.025, 0.02, 0.36), "armor")
        L.box("window bar h", "Chest", wc + Vector((0, -0.01, 0.05)), (0.18, 0.02, 0.025), "armor")
    else:
        # 金栅圣骸笼：上下框 + 竖栅，笼内白红火芯与火舌
        for k, z in enumerate((c.z - h / 2, zt)):
            L.trim(f"cage frame {k}", "Chest", [Vector((x * w / 2, c.y + y * d / 2, z)) for x, y in
                                                ((-1, -1), (1, -1), (1, 1), (-1, 1))], 0.024, "trim", n=4, closed=True)
        for k in range(10):
            a = TAU * (k + 0.5) / 10
            x, y = max(-1, min(1, 1.4 * math.sin(a))) * w / 2, max(-1, min(1, 1.4 * math.cos(a))) * d / 2
            L.trim(f"cage bar {k}", "Chest", [Vector((x, c.y + y, c.z - h / 2)), Vector((x, c.y + y, zt))], 0.014, "trim",
                   n=3)
        L.box("cage floor", "Chest", Vector((0, c.y, c.z - h / 2 + 0.02)), (w * 0.95, d * 0.95, 0.04), "armor")
        L.ell("relic fire", "Chest", c + Vector((0, 0, -0.06)), (0.15, 0.08, 0.20), "glow", 8, 5)
        # 火舌穿出敞口笼顶（俯视能看到火）
        for k in range(6):
            a = TAU * k / 6
            b = c + Vector((math.sin(a) * 0.12, math.cos(a) * 0.05, 0.05))
            L.spike(f"flame {k}", "Chest", b, b + Vector((math.sin(a) * 0.06, math.cos(a) * 0.03, 0.46 + 0.14 * (k % 2))),
                    0.055, "glow", sides=4, bend=(math.sin(a) * 0.03, 0, 0.02))
    if not E:
        # 人字顶 + 顶脊 + 顶尖
        roof = [(-d / 2 - 0.04, 0.0), (d / 2 + 0.04, 0.0), (0.0, 0.20)]
        L.plate("roof", "Chest", roof, w + 0.06, "armor", origin=(0, c.y, zt + 0.01), xaxis=(0, 1, 0), yaxis=(0, 0, 1))
        L.trim("roof ridge", "Chest", [Vector((-w / 2 - 0.05, c.y, zt + 0.215)), Vector((w / 2 + 0.05, c.y, zt + 0.215))],
               0.02, "trim", n=4)
        L.spike("roof finial", "Chest", Vector((0, c.y, zt + 0.21)), Vector((0, c.y - 0.02, zt + 0.42)), 0.035, "trim",
                sides=4)
    for k, (x, y, z, dx, dy, dz) in enumerate(((-w / 2, -d / 2, c.z + 0.15, -1, -0.6, 0.3), (w / 2, -d / 2, c.z + 0.15, 1, -0.6, 0.3),
                                                (-w / 2, -d / 2, c.z - 0.20, -1, -0.5, -0.2), (w / 2, -d / 2, c.z - 0.20, 1, -0.5, -0.2),
                                                (-w / 2, 0.0, zt + 0.02, -0.8, 0, 0.9), (w / 2, 0.0, zt + 0.02, 0.8, 0, 0.9),
                                                (0.0, -d / 2, c.z - 0.28, 0, -1, -0.3))):
        b = Vector((x, c.y + y, z))
        L.spike(f"box spike {k}", "Chest", b, b + Vector((dx, dy, dz)).normalized() * 0.24, 0.035, "armor", sides=4)
    for k, x in enumerate((-0.18, 0.18) if not E else (-0.27, 0.27)):
        for j, sy in enumerate((-1, 1)):
            b = Vector((x, c.y + sy * (0.07 if not E else 0.13), zt + (0.12 if not E else 0.0)))
            L.spike(f"roof spike {k}{j}", "Chest", b, b + Vector((x * 0.3, sy * 0.10, 0.20)), 0.03, "trim" if E else "armor",
                    sides=4)


def build(ctx, elite=False):
    L = Legion(ctx, elite, size=SIZE)
    E = elite
    H = pivot(WAIST, Matrix.Rotation(-HUNCH, 3, "X"))
    J = L.joint
    neck = H @ Vector((0, 0.05, 1.60))
    hc = neck + Vector((0, 0.11, -0.03))
    for side, lb in SIDES:
        J(f"hip.{lb}", (side * 0.16, 0.0, 0.88))
        J(f"knee.{lb}", (side * 0.17, 0.13, 0.48))
        J(f"ankle.{lb}", (side * 0.18, 0.0, 0.10))
        sh = J(f"shoulder.{lb}", H @ Vector((side * 0.36, 0.0, 1.50)))
        el = J(f"elbow.{lb}", sh + Vector((side * 0.08, 0.06, -0.36)))
        J(f"wrist.{lb}", el + Vector((0.0, 0.20, -0.27)))
    wr = L.J["wrist.R"]
    fist = wr + (wr - L.J["elbow.R"]).normalized() * 0.07
    ball = Vector((fist.x + 0.02, fist.y + 0.06, 0.30))
    L.bone("Root", (0, 0, 0), (0, 0, 0.25))
    L.bone("Pelvis", (0, 0, 0.86), (0, -0.01, 0.98), "Root")
    L.bone("Chest", WAIST, neck, "Pelvis")
    L.bone("Head", neck, neck + Vector((0, 0.14, 0.06)), "Chest")
    for side, lb in SIDES:
        L.bone(f"UpperArm.{lb}", L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], "Chest")
        L.bone(f"Forearm.{lb}", L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"], f"UpperArm.{lb}")
        L.bone(f"Thigh.{lb}", L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], "Pelvis")
        L.bone(f"Shin.{lb}", L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"], f"Thigh.{lb}")
    L.bone("Flail", fist, ball, "Forearm.R")
    L.translate["Pelvis"] = "_bob"

    # ----- 躯干（直立建模 → 前压）+ 背负圣物箱 -----
    L.xform = H
    L.tube("torso", "Chest", TORSO_P, TORSO_R, "armor", n=8, up=(0, 1, 0))
    L.cap("breastplate", "Chest", (0, 0.10, 1.34), (0, 1, 0.1), (0.34, 0.28, 0.19), "armor", theta=1.0, nu=8, nv=2,
          thick=0.016, fwd=(0, 0, 1))
    for k, z in enumerate((1.16, 1.24)):
        cy, dep, wid = section(TORSO_P, TORSO_R, z)
        for side in (-1, 1):
            pts = [Vector((side * wid * 1.05 * math.sin(a), cy + dep * 1.06 * math.cos(a), z - 0.03 * a))
                   for a in (0.25, 0.8, 1.35)]
            L.trim(f"scar rib {k}{side}", "Chest", pts, 0.014, "trim", n=4)
    build_box(L, E)
    L.xform = None
    # 斜挎锁链：左肩后 → 胸前 → 右髋（把箱子捆在身上）
    L.chain("bandolier", "Chest", [H @ Vector((-0.24, -0.25, 1.70)), H @ Vector((-0.27, 0.10, 1.60)),
                                   H @ Vector((-0.02, 0.29, 1.34)), H @ Vector((0.22, 0.22, 1.06))], "trim" if E else "armor",
            link=0.095, wire=0.013, width=0.05, lean=True)

    # ----- 头：布套兜帽 + 骨白面具三点竖排感光 -----
    L.cap("sack hood", "Head", hc + Vector((0, -0.02, 0.01)), (0, -0.3, 1), (0.14, 0.15, 0.15), "cloth", theta=1.95,
          nu=9, nv=3, phi=(0.95, TAU - 0.95))
    mask_c, mask_ax = hc + Vector((0, 0.05, -0.01)), Vector((0, 0.93, -0.36)).normalized()
    L.cap("mask", "Head", mask_c, mask_ax, (0.085, 0.10, 0.055), "trim", theta=1.2, nu=8, nv=2, fwd=(0, 0, 1), thick=0.01)
    face = mask_c + mask_ax * 0.055
    for k, dz in enumerate((0.035, 0.0, -0.035)):
        L.gem(f"tear {k}", "Head", face + Vector((0, 0.004, dz)), 0.017 if not E else 0.019, "glow", stretch=(1, 0.6, 0.9),
              sides=4)

    # ----- 巨臂 + 链环 + 拳；右拳链枷（Flail 骨） -----
    for side, lb in SIDES:
        sh, el, w = L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"]
        L.tube(f"upper arm {lb}", f"UpperArm.{lb}", [sh, el], [0.115, 0.09], "armor", n=6)
        L.tube(f"forearm {lb}", f"Forearm.{lb}", [el, w], [0.10, 0.085], "armor", n=6)
        for k, t in enumerate((0.3, 0.55, 0.8)):
            L.ring(f"arm chain {lb}{k}", f"Forearm.{lb}", el.lerp(w, t), w - el, 0.105 - 0.01 * t, 0.014,
                   "trim" if E else "armor", count=8, n=3)
        d = (w - el).normalized()
        L.ell(f"fist {lb}", f"Forearm.{lb}", w + d * 0.07, (0.09, 0.095, 0.09), "armor", 6, 4)
        pc, pax = sh + Vector((side * 0.03, -0.01, 0.05)), (side * 0.5, -0.1, 0.86)
        pr = (0.17, 0.17, 0.12) if not E else (0.20, 0.20, 0.15)
        L.cap(f"pauldron {lb}", "Chest", pc, pax, pr, "armor", theta=1.3, nu=8, nv=2, thick=0.018)
        L.trim(f"pauldron rim {lb}", "Chest", cap_rim(pc, pax, pr, 1.3, 8, grow=0.004), 0.012, "trim", n=3, closed=True)
        if E:
            top = pc + Vector(pax).normalized() * pr[2]
            L.spike(f"pauldron spike {lb}", "Chest", top, top + Vector((side * 0.08, -0.02, 0.18)), 0.035, "trim", sides=4)
    L.chain("flail chain", "Flail", [fist + Vector((0, 0, -0.06)), ball + Vector((0, 0, 0.08))], "trim" if E else "armor",
            link=0.075, wire=0.011, width=0.04, lean=True)
    L.ell("flail ball", "Flail", ball, (0.085, 0.085, 0.085), "armor", 8, 5)
    for k, v in enumerate(((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, -1), (0.6, 0.6, 0.5), (-0.6, -0.6, 0.5))):
        dv = Vector(v).normalized()
        L.spike(f"flail spike {k}", "Flail", ball + dv * 0.07, ball + dv * 0.15, 0.025, "trim" if E else "armor", sides=3)

    # ----- 骨盆：髋管 + 腰带 + 破布兜裆 -----
    L.tube("hips", "Pelvis", [(0, -0.01, 0.80), (0, -0.01, 0.90), (0, -0.01, 1.02)], [(0.16, 0.21), (0.19, 0.25), (0.17, 0.22)],
           "armor", n=8, up=(0, 1, 0))
    L.ring("belt", "Pelvis", (0, -0.01, 0.97), (0, 0, 1), 0.26, 0.02, "cloth", count=10, n=3, squash=0.75)
    L.strip("loin front", "Pelvis", (0, 0.18, 0.96), (0, 0.25, -1), (1, 0, 0), 0.15, 0.40, jag=(0.8, 1.0, 0.7), cup=0.02)
    for k, x in enumerate((-0.12, 0.0, 0.12)):
        L.strip(f"loin back {k}", "Pelvis", (x, -0.17, 0.97), (x * 0.4, -0.3, -1), (1, 0, 0), 0.12, 0.42 + 0.06 * (k == 1),
                jag=((0.7, 1.0, 0.8) if k != 1 else (1.0, 0.7, 0.9)), cup=-0.015)

    # ----- 腿 -----
    for side, lb in SIDES:
        hp, kn, an = L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"]
        th, sn = f"Thigh.{lb}", f"Shin.{lb}"
        L.tube(f"thigh {lb}", th, [hp, kn], [0.12, 0.095], "armor", n=6)
        L.cap(f"knee {lb}", sn, kn + Vector((0, 0.045, 0.0)), (0, 1, 0.2), (0.095, 0.095, 0.07), "armor", theta=1.2, nu=7,
              nv=2, thick=0.012)
        L.tube(f"shin {lb}", sn, [kn, an], [0.09, 0.075], "armor", n=6)
        L.wrap(f"greave {lb}", sn, kn.lerp(an, 0.12), kn.lerp(an, 0.88), 0.105, 0.09, (0, 1, 0), "armor", arc=2.4, nu=4,
               nv=2, thick=0.012)
        x = an.x
        L.tube(f"foot {lb}", sn, [(x, -0.10, 0.075), (x, 0.03, 0.075), (x, 0.21, 0.045)],
               [(0.105, 0.075), (0.105, 0.09), (0.05, 0.06)], "armor", n=4, up=(0, 0, 1), twist=math.pi / 4)

    if E:
        L.halo_crown("halo crown", "Head", hc + Vector((0, -0.09, 0.12)), (0, -0.5, 0.87), 0.20, spikes=9, length=0.09,
                     r=0.009, tilt=0.35)
    return L.finalize(fist=fist, ball=ball)


# ===== 动作 =====
REVIEW_POSE = ("Attack", 1)


def stand(rig, st):
    p = {}
    shift(p, st, z=-0.02)
    for lb in ("L", "R"):
        plant(rig, st, p, lb, (0, 0, 0), ((-1 if lb == "L" else 1) * 0.12, 1, 0))
    return p


def move(rig, st, t):
    """负箱苦行：宽步沉重前压、上身随步左右晃；左拳前后摆，右拳拖着链枷，链枷滞后半拍来回荡。"""
    p = {}
    shift(p, st, z=-0.04 + 0.025 * math.cos(2 * (t - 1.8)))
    p["Pelvis"] = R((Z, -0.08 * math.cos(t)), (Y, 0.06 * math.sin(t)))
    p["Chest"] = R((X, -(0.03 + 0.03 * math.cos(2 * t))), (Z, 0.10 * math.cos(t)), (Y, -0.07 * math.sin(t)))
    p["Head"] = R((X, 0.04 * math.cos(2 * t)), (Z, -0.05 * math.cos(t)))
    p["UpperArm.L"] = R((X, -0.30 * math.cos(t)))
    p["Forearm.L"] = R((X, 0.10 + 0.10 * math.sin(t)))
    p["UpperArm.R"] = R((X, 0.22 * math.cos(t)))
    p["Forearm.R"] = R((X, 0.05))
    p["Flail"] = R((X, -0.30 * math.cos(t - 0.9)), (Y, 0.10 * math.sin(t)))
    steps(rig, st, p, t, stride=0.40, lift=0.12, stance=0.62, width=0.01, pole_out=0.12)
    return p


def smash_key(rig, st, stage):
    """链枷砸地：1 右臂后扬、链枷甩到身后 / 2 越顶 / 3 砸在身前地面 / 4 余势。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=-0.05)
        p["Pelvis"] = R((Z, -0.14))
        p["Chest"] = R((Z, -0.30), (X, 0.10))
        p["Head"] = R((Z, 0.2))
        rig.aim(p, "UpperArm.R", (0.50, -0.55, 0.30))
        rig.aim(p, "Forearm.R", (0.30, -0.70, 0.30))
        rig.aim(p, "Flail", (0.10, -0.85, -0.50))
        rig.aim(p, "UpperArm.L", (-0.40, 0.60, -0.70))
        plant(rig, st, p, "L", (0, 0.06, 0), (-0.12, 1, 0))
        plant(rig, st, p, "R", (0, -0.08, 0), (0.12, 1, 0))
    elif stage == 2:
        shift(p, st, z=-0.03)
        p["Chest"] = R((Z, -0.05), (X, 0.12))
        rig.aim(p, "UpperArm.R", (0.35, 0.10, 0.93))
        rig.aim(p, "Forearm.R", (0.15, 0.20, 0.97))
        rig.aim(p, "Flail", (0.05, -0.60, 0.80))
        rig.aim(p, "UpperArm.L", (-0.40, 0.30, -0.86))
        plant(rig, st, p, "L", (0, 0.10, 0), (-0.12, 1, 0))
        plant(rig, st, p, "R", (0, -0.08, 0), (0.12, 1, 0))
    else:
        f = stage == 4
        shift(p, st, z=-0.12, y=0.08)
        p["Pelvis"] = R((Z, 0.10), (X, 0.06))
        p["Chest"] = R((Z, 0.20), (X, -0.30 if not f else -0.34))
        p["Head"] = R((X, 0.15))
        rig.aim(p, "UpperArm.R", (0.05, 0.85, -0.52))
        rig.aim(p, "Forearm.R", (0.0, 0.70, -0.72))
        rig.aim(p, "Flail", (0.0, 0.72, -0.69) if not f else (0.0, 0.35, -0.94))
        rig.aim(p, "UpperArm.L", (-0.40, -0.30, -0.86))
        plant(rig, st, p, "L", (0, 0.22, 0), (-0.12, 1, 0))
        plant(rig, st, p, "R", (0, -0.10, 0), (0.12, 1, 0))
    return p


def blaze_key(rig, st, stage):
    """精英殉道暴燃：1 抱臂蜷身蓄力 / 2 双臂猛张、挺胸后仰（笼火朝天）/ 3 保持。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=-0.10)
        p["Chest"] = R((X, -0.25))
        p["Head"] = R((X, -0.15))
        for lb, sg in (("L", -1), ("R", 1)):
            rig.aim(p, f"UpperArm.{lb}", (sg * 0.10, 0.80, -0.60))
            rig.aim(p, f"Forearm.{lb}", (-sg * 0.75, 0.55, 0.10))
        rig.aim(p, "Flail", (0.0, 0.2, -1.0))
        for lb in ("L", "R"):
            plant(rig, st, p, lb, (0, 0, 0), ((-1 if lb == "L" else 1) * 0.2, 1, 0))
    else:
        k = 1.0 if stage == 2 else 0.85
        shift(p, st, z=-0.03)
        p["Chest"] = R((X, 0.30 * k))
        p["Head"] = R((X, 0.25 * k))
        for lb, sg in (("L", -1), ("R", 1)):
            rig.aim(p, f"UpperArm.{lb}", (sg * 0.92, 0.10, 0.35 * k))
            rig.aim(p, f"Forearm.{lb}", (sg * 0.85, 0.20, 0.50 * k))
        rig.aim(p, "Flail", (0.6, 0.2, -0.78))
        for lb in ("L", "R"):
            plant(rig, st, p, lb, ((-1 if lb == "L" else 1) * 0.04, 0, 0), ((-1 if lb == "L" else 1) * 0.2, 1, 0))
    return p


def animate(rig, st):
    rig.loop("Move", 24, lambda t: move(rig, st, t), step=1)
    if st["elite"]:
        k = [blaze_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (8, k[1]), (12, k[2]), (17, k[3]), (24, k[0])])
    else:
        k = [smash_key(rig, st, i) for i in range(5)]
        rig.keyed("Attack", [(1, k[0]), (7, k[1]), (10, k[2]), (12, k[3]), (15, k[4]), (21, k[0])])
