"""香炉炮手 Censer Gunner（mob-4）/ 香炉审判官 Censer Inquisitor（elite-4）。

长袍炮手：钟形重袍（枪铁“法衣”，骨白下摆环与前襟带，破边垂片），肩披 + 兜帽下骨白面具一道猩红竖缝；
右肩扛一门香炉炮——后部是骨白三环笼住的薄荷绿炉心，顶上三根短烟囱冒出薄荷绿烟团，前伸枪铁长炮管
（骨白箍环、喇叭炮口内一圈薄荷光），炉底垂一小段链。双手握炮，手臂刚性挂在 Chest 上（端炮不摆臂），
炮身单独挂 Cannon 骨做后坐。骨架 9 节。俯视：右侧一条长炮管 + 肩头一团薄荷光。
远程单位只有 4 种材质：枪铁（兼作长袍）、骨白（精英暗金）、猩红感光、薄荷绿武器光。
精英：放大 1.3 倍，双肩双炮（镜像）、金边法衣、尖刺光冠、白红胸核；Attack 为双炮上扬抛射（地面范围圈）。
"""

import math

from mathutils import Vector

from chars._legion import MINT, SIDES, TAU, Legion, R, X, Y, Z, cap_rim, plant, shift, steps

SIZE = 0.955


def build_cannon(L, side, E):
    """一门香炉炮（side=+1 右肩 / -1 左肩），全部挂 Cannon 骨。"""
    B = "Cannon"
    cc = Vector((side * 0.31, -0.06, 1.62))            # 炉心
    L.ell(f"censer core {side}", B, cc, (0.085, 0.085, 0.085), "weapon", 6, 4)
    for k, ax in enumerate(((0, 0, 1), (1, 0, 0.35), (-1, 0, 0.35))):
        L.ring(f"censer cage {side}{k}", B, cc, ax, 0.12, 0.012, "trim", count=10, n=3, fwd=(0, 1, 0))
    L.ell(f"censer cap {side}", B, cc + Vector((0, 0, 0.11)), (0.07, 0.07, 0.035), "armor", 6, 3)
    for k, (dx, dy) in enumerate(((-0.035, -0.03), (0.035, -0.03), (0.0, 0.04))):
        b = cc + Vector((dx, dy, 0.10))
        L.tube(f"chimney {side}{k}", B, [b, b + Vector((dx * 0.3, dy * 0.3, 0.07))], [0.016, 0.012], "armor", n=5)
        L.ell(f"smoke {side}{k}", B, b + Vector((dx * 0.9, dy * 0.9 - 0.02, 0.14 + 0.05 * k)),
              (0.042 + 0.012 * k, 0.042 + 0.012 * k, 0.032 + 0.01 * k), "weapon", 8, 5)
    # 炮管 + 箍环 + 喇叭口
    b0, b1 = cc + Vector((0, 0.09, -0.01)), cc + Vector((0, 0.92, -0.05))
    L.tube(f"barrel {side}", B, [b0, b1], [0.065, 0.055], "armor", n=8)
    for k, t in enumerate((0.12, 0.45, 0.78)):
        L.ring(f"barrel band {side}{k}", B, b0.lerp(b1, t), b1 - b0, 0.072 - 0.008 * t, 0.013, "trim", count=8, n=3,
               fwd=(0, 0, 1))
    d = (b1 - b0).normalized()
    L.tube(f"muzzle {side}", B, [b1 - d * 0.02, b1 + d * 0.06, b1 + d * 0.12], [0.06, 0.085, 0.10], "armor", n=8,
           cap=False)
    L.ring(f"muzzle glow {side}", B, b1 + d * 0.10, d, 0.078, 0.014, "weapon", count=8, n=3, fwd=(0, 0, 1))
    # 肩托、握把、垂链
    L.box(f"mount {side}", B, cc + Vector((-side * 0.09, 0.05, -0.10)), (0.10, 0.20, 0.06), "armor")
    L.tube(f"rear grip {side}", B, [cc + Vector((0, 0.20, -0.06)), cc + Vector((0, 0.24, -0.20))], [0.02, 0.02], "armor", n=5)
    L.tube(f"front grip {side}", B, [b0.lerp(b1, 0.55) + Vector((0, 0, -0.05)), b0.lerp(b1, 0.58) + Vector((-side * 0.02, 0, -0.18))],
           [0.02, 0.02], "armor", n=5)
    L.chain(f"censer chain {side}", B, [cc + Vector((0, -0.02, -0.12)), cc + Vector((side * 0.02, -0.04, -0.34))], "armor",
            link=0.055, wire=0.008, width=0.03)
    return cc, b0, b1


def build(ctx, elite=False):
    L = Legion(ctx, elite, weapon=("censer mint glow", MINT), size=SIZE)
    E = elite
    J = L.joint
    for side, lb in SIDES:
        J(f"hip.{lb}", (side * 0.11, 0.0, 0.92))
        J(f"knee.{lb}", (side * 0.115, 0.09, 0.50))
        J(f"ankle.{lb}", (side * 0.12, -0.01, 0.09))
    L.bone("Root", (0, 0, 0), (0, 0, 0.25))
    L.bone("Pelvis", (0, 0, 0.90), (0, 0, 1.06), "Root")
    L.bone("Chest", (0, 0, 1.06), (0, 0.06, 1.55), "Pelvis")
    L.bone("Head", (0, 0.07, 1.55), (0, 0.12, 1.78), "Chest")
    L.bone("Cannon", (0, -0.06, 1.60), (0, 0.40, 1.60), "Chest")
    for side, lb in SIDES:
        L.bone(f"Thigh.{lb}", L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], "Pelvis")
        L.bone(f"Shin.{lb}", L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"], f"Thigh.{lb}")
    L.translate["Pelvis"] = "_bob"
    L.translate["Cannon"] = "_recoil"

    # ----- 钟形法衣（挂 Pelvis，腿在袍内小步走） -----
    rp = [(0, 0.0, 1.07), (0, 0.0, 0.92), (0, -0.01, 0.66), (0, -0.02, 0.40), (0, -0.02, 0.23)]
    rr = [(0.15, 0.18), (0.19, 0.22), (0.27, 0.29), (0.34, 0.36), (0.37, 0.39)]
    L.tube("robe", "Pelvis", rp, rr, "armor", n=10, up=(0, 1, 0), cap=False, sharp=20)
    L.ring("robe hem", "Pelvis", (0, -0.02, 0.235), (0, 0, 1), 0.395, 0.016, "trim", count=12, n=3, squash=0.95)
    L.ring("robe girdle", "Pelvis", (0, 0.0, 1.0), (0, 0, 1), 0.205, 0.02, "trim", count=10, n=3, squash=0.86)
    band = [Vector((0, rr[i][0] + rp[i][1] + 0.012, rp[i][2])) for i in range(1, 5)]
    L.tube("robe front band", "Pelvis", band, [(0.008, 0.05)] * 4, "trim", n=4, up=(0, 1, 0))
    for k in range(8):
        a = TAU * (k + 0.5) / 8
        r = 0.385
        top = Vector((math.sin(a) * r, -0.02 + math.cos(a) * r * 0.95, 0.25))
        L.strip(f"hem tatter {k}", "Pelvis", top, (math.sin(a) * 0.3, math.cos(a) * 0.3, -1), (math.cos(a), -math.sin(a), 0),
                0.13, 0.11 + 0.05 * (k % 3 == 0), jag=((0.6, 1.0, 0.7) if k % 2 else (1.0, 0.65, 0.9)), nv=2, mat="cloth")

    # ----- 上身：躯干 + 肩披 + 兜帽 + 骨白面具竖缝 -----
    L.tube("torso", "Chest", [(0, 0.0, 1.04), (0, 0.02, 1.25), (0, 0.05, 1.45), (0, 0.07, 1.56)],
           [(0.14, 0.17), (0.16, 0.22), (0.15, 0.23), (0.08, 0.12)], "armor", n=8, up=(0, 1, 0))
    mc, max_, mr, mth = Vector((0, 0.02, 1.47)), (0, -0.2, 1), (0.30, 0.25, 0.15), 1.5
    L.cap("mantle", "Chest", mc, max_, mr, "armor", theta=mth, nu=10, nv=3, phi=(0.7, TAU - 0.7), thick=0.012)
    L.trim("mantle rim", "Chest", cap_rim(mc, max_, mr, mth, 10, phi=(0.7, TAU - 0.7), grow=0.004), 0.011, "trim", n=3)
    hc = Vector((0, 0.10, 1.68))
    L.cap("cowl", "Head", hc + Vector((0, -0.02, 0)), (0, -0.3, 1), (0.13, 0.145, 0.15), "armor", theta=1.9, nu=9, nv=3,
          phi=(0.9, TAU - 0.9), thick=0.01,
          shape=lambda p, th, ph: p + Vector((0, -0.04 * (1 - th / 1.9) ** 2, 0.05 * (1 - th / 1.9) ** 3)))
    mask_c, mask_ax = hc + Vector((0, 0.045, -0.01)), Vector((0, 0.97, -0.15)).normalized()
    L.cap("mask", "Head", mask_c, mask_ax, (0.078, 0.10, 0.052), "trim", theta=1.2, nu=8, nv=2, fwd=(0, 0, 1), thick=0.01)
    face = mask_c + mask_ax * 0.052
    L.tube("sight slit", "Head", [face + Vector((0, 0.0, 0.05)), face + Vector((0, 0.006, 0.0)), face + Vector((0, 0, -0.045))],
           [0.008, 0.012, 0.008], "glow", n=4)
    # 呼吸滤罐 + 肋管（从面具下接到胸前）
    for side in (-1, 1):
        L.cable(f"breather {side}", "Head", [face + Vector((side * 0.035, -0.02, -0.07)), hc + Vector((side * 0.09, 0.06, -0.14)),
                                            Vector((side * 0.10, 0.17, 1.46))], 0.017, "armor", per=3, n=5)

    # ----- 炮（右肩；精英双肩镜像）+ 端炮双臂（刚性挂 Chest） -----
    sides = (1, -1) if E else (1,)
    for side in sides:
        cc, b0, b1 = build_cannon(L, side, E)
    for side, lb in SIDES:
        sh = Vector((side * 0.235, 0.02, 1.50))
        if E:
            el = Vector((side * 0.36, 0.06, 1.30))
            hand = Vector((side * 0.31, 0.18, 1.42))
        elif side > 0:
            el, hand = Vector((0.36, 0.06, 1.30)), Vector((0.31, 0.18, 1.42))
        else:
            el, hand = Vector((-0.20, 0.24, 1.28)), Vector((0.27, 0.46, 1.43))
        L.tube(f"upper arm {lb}", "Chest", [sh, el], [0.05, 0.042], "armor", n=6)
        L.tube(f"forearm {lb}", "Chest", [el, hand], [0.042, 0.036], "armor", n=6)
        L.wrap(f"vambrace {lb}", "Chest", el.lerp(hand, 0.15), el.lerp(hand, 0.85), 0.052, 0.046, (0, -0.3, -1), "armor",
               arc=2.6, nu=4, nv=2, thick=0.01)
        L.ell(f"glove {lb}", "Chest", hand, (0.045, 0.05, 0.045), "armor", 6, 4)
        pc, pax, pr = sh + Vector((side * 0.02, -0.01, 0.04)), (side * 0.55, -0.1, 0.83), (0.11, 0.11, 0.08) if not E else (0.13, 0.13, 0.10)
        L.cap(f"pauldron {lb}", "Chest", pc, pax, pr, "armor", theta=1.3, nu=7, nv=2, thick=0.012)
        L.trim(f"pauldron rim {lb}", "Chest", cap_rim(pc, pax, pr, 1.3, 7, grow=0.004), 0.009, "trim", n=3, closed=True)

    # ----- 腿（袍下只露小腿与靴） -----
    for side, lb in SIDES:
        hp, kn, an = L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"]
        L.tube(f"thigh {lb}", f"Thigh.{lb}", [hp, kn], [0.07, 0.055], "armor", n=6)
        L.tube(f"shin {lb}", f"Shin.{lb}", [kn, an], [0.055, 0.045], "armor", n=6)
        L.wrap(f"greave {lb}", f"Shin.{lb}", kn.lerp(an, 0.3), kn.lerp(an, 0.92), 0.065, 0.058, (0, 1, 0), "armor", arc=2.4,
               nu=4, nv=2, thick=0.01)
        x = an.x
        L.tube(f"boot {lb}", f"Shin.{lb}", [(x, -0.08, 0.055), (x, 0.03, 0.055), (x, 0.17, 0.03)],
               [(0.075, 0.055), (0.075, 0.06), (0.035, 0.04)], "armor", n=4, up=(0, 0, 1), twist=math.pi / 4)

    if E:
        L.halo_crown("halo crown", "Head", hc + Vector((0, -0.10, 0.10)), (0, -0.6, 0.8), 0.19, spikes=9, length=0.09,
                     r=0.009, tilt=0.35)
        L.gem("core", "Chest", (0, 0.24, 1.30), 0.04, "glow", stretch=(0.8, 0.5, 1.3), sides=4)
        L.ring("core rim", "Chest", (0, 0.225, 1.30), (0, 1, 0), 0.05, 0.009, "trim", count=8, n=3, fwd=(0, 0, 1))
    return L.finalize()


# ===== 动作 =====
REVIEW_POSE = ("Attack", 1)


def stand(rig, st):
    p = {}
    shift(p, st, z=-0.015)
    for lb in ("L", "R"):
        plant(rig, st, p, lb, (0, 0, 0), ((-1 if lb == "L" else 1) * 0.12, 1, 0))
    return p


def move(rig, st, t):
    """端炮稳步：袍下小步快走、法衣左右摆，上身与炮口保持瞄准，只有轻微起伏。"""
    p = {}
    shift(p, st, z=-0.03 + 0.018 * math.cos(2 * (t - 1.8)))
    p["Pelvis"] = R((Z, -0.07 * math.cos(t)), (Y, 0.05 * math.sin(t)))
    p["Chest"] = R((Z, 0.06 * math.cos(t)), (Y, -0.04 * math.sin(t)), (X, -0.03))
    p["Head"] = R((Z, 0.02 * math.cos(t)))
    p["Cannon"] = R((X, 0.02 * math.sin(2 * t)))
    steps(rig, st, p, t, stride=0.30, lift=0.09, stance=0.6, pole_out=0.12)
    return p


def fire_key(rig, st, stage):
    """开炮：1 前倾抵肩 / 2 后坐（炮身后滑上扬、上身被顶回）/ 3 回稳。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=-0.04)
        p["Chest"] = R((X, -0.08))
        p["Cannon"] = R((X, -0.03))
        plant(rig, st, p, "L", (0, 0.08, 0), (-0.12, 1, 0))
        plant(rig, st, p, "R", (0, -0.06, 0), (0.12, 1, 0))
    else:
        k = 1.0 if stage == 2 else 0.35
        shift(p, st, z=-0.05, y=-0.03 * k)
        p["Chest"] = R((X, 0.12 * k - 0.04))
        p["Head"] = R((X, 0.06 * k))
        p["Cannon"] = R((X, 0.08 * k))
        p["_recoil"] = Vector((0, -0.045 * k * st["s"], 0.0))
        plant(rig, st, p, "L", (0, 0.08, 0), (-0.12, 1, 0))
        plant(rig, st, p, "R", (0, -0.06, 0), (0.12, 1, 0))
    return p


def lob_key(rig, st, stage):
    """精英双炮抛射：1 下蹲、双炮高仰 / 2 齐射后坐 / 3 回稳。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    k = {1: 0.0, 2: 1.0, 3: 0.4}[stage]
    shift(p, st, z=-0.07, y=-0.02 * k)
    p["Chest"] = R((X, 0.12 + 0.06 * k))
    p["Head"] = R((X, 0.10))
    p["Cannon"] = R((X, 0.62 + 0.12 * k))
    p["_recoil"] = Vector((0, -0.08 * k * st["s"], -0.03 * k * st["s"]))
    plant(rig, st, p, "L", (-0.03, 0.06, 0), (-0.2, 1, 0))
    plant(rig, st, p, "R", (0.03, -0.08, 0), (0.2, 1, 0))
    return p


def animate(rig, st):
    rig.loop("Move", 20, lambda t: move(rig, st, t), step=1)
    if st["elite"]:
        k = [lob_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (7, k[1]), (10, k[2]), (15, k[3]), (22, k[0])])
    else:
        k = [fire_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (5, k[1]), (7, k[2]), (11, k[3]), (17, k[0])])
