"""圣骸巨像 Reliquary Colossus（mob-7，无精英）。

3.2 m 的石甲巨像：六棱切面的枪铁躯干上压着一块块厚石板（硬边切面，缝里透出猩红裂光），巨肩圆甲 + 骨白滚边，
小头缩在两肩之间、骨白面板上三点横排猩红感光；两条长臂垂到膝下，末端是带骨白指节刺的方块巨拳；
背上斜背一口六角棺形圣骸（骨白棺缘、棺盖猩红十字窗、两道锁链捆在背上、棺底垂破殓布）。
俯视：最大的体量 + 背上一口长六角棺 + 两只大拳。骨架 12 节。
"""

import math

from mathutils import Matrix, Vector

from chars._legion import SIDES, Legion, R, X, Y, Z, cap_rim, pivot, plant, section, shift, steps

SIZE = 1.0
TORSO_P = [(0, 0.0, 1.22), (0, 0.0, 1.42), (0, 0.02, 1.78), (0, 0.02, 2.12), (0, 0.0, 2.36)]
TORSO_R = [(0.33, 0.40), (0.36, 0.46), (0.46, 0.60), (0.45, 0.64), (0.27, 0.40)]
WAIST = Vector((0, 0.0, 1.30))
HUNCH = 0.30
COFFIN_C = Vector((0, -0.66, 2.02))
COFFIN_AX = Vector((0, -0.22, 1)).normalized()


def build(ctx, elite=False):
    L = Legion(ctx, elite, size=SIZE)
    H = pivot(WAIST, Matrix.Rotation(-HUNCH, 3, "X"))
    J = L.joint
    neck = H @ Vector((0, 0.10, 2.34))
    hc = neck + Vector((0, 0.12, 0.06))
    for side, lb in SIDES:
        J(f"hip.{lb}", (side * 0.28, 0.0, 1.20))
        J(f"knee.{lb}", (side * 0.30, 0.15, 0.66))
        J(f"ankle.{lb}", (side * 0.32, 0.0, 0.15))
        sh = J(f"shoulder.{lb}", H @ Vector((side * 0.64, 0.0, 2.16)))
        el = J(f"elbow.{lb}", sh + Vector((side * 0.14, 0.02, -0.56)))
        J(f"wrist.{lb}", el + Vector((-side * 0.02, 0.30, -0.44)))
    L.bone("Root", (0, 0, 0), (0, 0, 0.4))
    L.bone("Pelvis", (0, 0, 1.16), (0, 0, 1.34), "Root")
    L.bone("Chest", WAIST, neck, "Pelvis")
    L.bone("Head", neck, neck + Vector((0, 0.12, 0.20)), "Chest")
    for side, lb in SIDES:
        L.bone(f"UpperArm.{lb}", L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], "Chest")
        L.bone(f"Forearm.{lb}", L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"], f"UpperArm.{lb}")
        L.bone(f"Thigh.{lb}", L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], "Pelvis")
        L.bone(f"Shin.{lb}", L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"], f"Thigh.{lb}")
    L.translate["Pelvis"] = "_bob"

    # ----- 躯干（直立建模 → 前压）：六棱切面躯干 + 厚石板 + 猩红裂光 + 背负六角棺 -----
    L.xform = H
    L.tube("torso", "Chest", TORSO_P, TORSO_R, "armor", n=6, up=(0, 1, 0), twist=math.pi / 6, sharp=35)
    slabs = [((0, 0.46, 1.94), (0.54, 0.12, 0.36), (0, 0, 0)), ((-0.21, 0.40, 1.60), (0.34, 0.10, 0.26), (0, 0, 0.18)),
             ((0.21, 0.40, 1.60), (0.34, 0.10, 0.26), (0, 0, -0.18)), ((0, 0.34, 1.34), (0.40, 0.10, 0.18), (0, 0, 0))]
    for k, (c, s, rz) in enumerate(slabs):
        L.box(f"chest slab {k}", "Chest", c, s, "armor", rot=Matrix.Rotation(rz[2], 3, "Z") @ Matrix.Rotation(-0.12, 3, "X"),
              taper=(0.9, 0.8))
    L.trim("chest slab rim", "Chest", [Vector((x, 0.53, z)) for x, z in ((-0.27, 1.76), (-0.27, 2.12), (0.27, 2.12), (0.27, 1.76))],
           0.02, "trim", n=3, closed=True)
    for k, pts in enumerate((((-0.02, 1.76), (0.03, 1.70), (-0.01, 1.62), (0.04, 1.50)),
                             ((-0.30, 1.86), (-0.38, 1.74), (-0.36, 1.60)), ((0.30, 1.86), (0.37, 1.72), (0.40, 1.62)))):
        L.tube(f"glow crack {k}", "Chest", [Vector((x, section(TORSO_P, TORSO_R, z)[1] + 0.02 - 0.12 * abs(x), z)) for x, z in pts],
               [0.014] * len(pts), "glow", n=4)
    # 六角棺：棺体 + 骨白棺缘 + 猩红十字窗 + 棺钉
    cz = COFFIN_AX
    cx = Vector((1, 0, 0))
    cn = cz.cross(cx)          # 棺盖朝后
    outline = [(0.0, 0.96), (-0.25, 0.80), (-0.36, 0.48), (-0.24, -0.96), (0.24, -0.96), (0.36, 0.48), (0.25, 0.80)]
    L.plate("coffin", "Chest", outline, 0.36, "armor", origin=COFFIN_C, xaxis=cx, yaxis=cz, bev=0.02)
    lid = COFFIN_C + cn * 0.185
    L.trim("coffin rim", "Chest", [lid + cx * x * 1.02 + cz * y * 1.01 for x, y in outline], 0.024, "trim", n=3, closed=True)
    L.trim("coffin rim back", "Chest", [COFFIN_C - cn * 0.185 + cx * x * 1.02 + cz * y * 1.01 for x, y in outline], 0.02,
           "trim", n=3, closed=True)
    # 棺盖（朝外的背面）大十字 + 贴背一面的小十字（从正面越过头顶也能看到）
    back = COFFIN_C - cn * 0.197
    L.tube("coffin cross v", "Chest", [back + cz * 0.62, back + cz * -0.40], [0.034, 0.034], "glow", n=4)
    L.tube("coffin cross h", "Chest", [back + cz * 0.34 + cx * -0.20, back + cz * 0.34 + cx * 0.20], [0.034, 0.034], "glow", n=4)
    L.tube("front cross v", "Chest", [lid + cn * 0.012 + cz * 0.70, lid + cn * 0.012 + cz * 0.25], [0.026, 0.026], "glow", n=4)
    L.tube("front cross h", "Chest", [lid + cn * 0.012 + cz * 0.56 + cx * -0.12, lid + cn * 0.012 + cz * 0.56 + cx * 0.12],
           [0.026, 0.026], "glow", n=4)
    for k, (x, y) in enumerate(((-0.28, 0.55), (0.28, 0.55), (-0.2, -0.85), (0.2, -0.85), (0.0, 0.88))):
        L.gem(f"coffin stud {k}", "Chest", back + cx * x + cz * y, 0.04, "trim", stretch=(1, 1, 0.7), sides=4)
    L.xform = None
    # 两道锁链把棺材捆在背上（从肩后绕到棺背）
    for side in (-1, 1):
        L.chain(f"coffin chain {side}", "Chest", [H @ Vector((side * 0.52, 0.10, 2.20)), H @ Vector((side * 0.42, -0.62, 2.30)),
                                                   H @ Vector((side * 0.10, -0.90, 2.28))], "armor", link=0.13, wire=0.02,
                width=0.08, lean=True)
    # 棺底垂下的破殓布
    bot = H @ (COFFIN_C - COFFIN_AX * 0.90 - cn * 0.05)
    for k, x in enumerate((-0.16, 0.0, 0.16)):
        L.strip(f"shroud {k}", "Chest", bot + Vector((x, 0, 0)), (x * 0.5, -0.25, -1), (1, 0, 0), 0.16, 0.55 + 0.15 * (k == 1),
                jag=((0.7, 1.0, 0.8) if k != 1 else (1.0, 0.7, 0.9)), cup=-0.02, nv=3)

    # ----- 头：缩肩小头 + 骨白面板 + 三点横排感光 -----
    L.box("head block", "Head", hc, (0.26, 0.26, 0.24), "armor", taper=(0.85, 0.85), bev=0.02)
    L.plate("face slab", "Head", [(-0.12, 0.10), (0.12, 0.10), (0.13, -0.04), (0.06, -0.13), (-0.06, -0.13), (-0.13, -0.04)],
            0.03, "trim", origin=hc + Vector((0, 0.135, 0.0)), xaxis=(1, 0, 0), yaxis=(0, -0.1, 1))
    for k, x in enumerate((-0.06, 0.0, 0.06)):
        L.gem(f"sensor {k}", "Head", hc + Vector((x, 0.158, 0.02)), 0.022, "glow", stretch=(1, 0.6, 0.8), sides=4)
    L.spike("brow ridge", "Head", hc + Vector((-0.14, 0.12, 0.10)), hc + Vector((0.14, 0.12, 0.10)), 0.03, "armor", sides=4)

    # ----- 巨肩 + 长臂 + 方块巨拳 -----
    for side, lb in SIDES:
        sh, el, wr = L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"]
        pc, pax, pr = sh + Vector((side * 0.06, -0.02, 0.10)), (side * 0.5, -0.05, 0.86), (0.34, 0.34, 0.24)
        L.cap(f"pauldron {lb}", "Chest", pc, pax, pr, "armor", theta=1.3, nu=6, nv=2, thick=0.04, sharp=35)
        L.trim(f"pauldron rim {lb}", "Chest", cap_rim(pc, pax, pr, 1.3, 6, grow=0.006), 0.022, "trim", n=3, closed=True)
        top = pc + Vector(pax).normalized() * pr[2]
        for k, dy in enumerate((-0.14, 0.12)):
            b = top + Vector((0, dy, -0.02))
            L.box(f"shoulder stone {lb}{k}", "Chest", b, (0.18, 0.14, 0.14), "armor",
                  rot=Matrix.Rotation(side * 0.4, 3, "Y"), taper=(0.6, 0.7))
        ua, fa = f"UpperArm.{lb}", f"Forearm.{lb}"
        L.tube(f"upper arm {lb}", ua, [sh, el], [0.18, 0.15], "armor", n=6, sharp=35)
        L.box(f"bicep slab {lb}", ua, sh.lerp(el, 0.55) + Vector((side * 0.13, 0.0, 0.0)), (0.08, 0.26, 0.34), "armor",
              taper=(0.8, 0.8))
        L.tube(f"forearm {lb}", fa, [el, wr], [0.16, 0.17], "armor", n=6, sharp=35)
        L.ring(f"wrist band {lb}", fa, el.lerp(wr, 0.78), wr - el, 0.19, 0.03, "trim", count=6, n=3)
        L.ring(f"elbow band {lb}", fa, el.lerp(wr, 0.12), wr - el, 0.175, 0.026, "trim", count=6, n=3)
        d = (wr - el).normalized()
        fist = wr + d * 0.17
        L.box(f"fist {lb}", fa, fist, (0.34, 0.34, 0.36), "armor", rot=Matrix.Rotation(-0.6, 3, "X"), bev=0.03)
        for k, dx in enumerate((-0.10, 0.0, 0.10)):
            b = fist + d * 0.15 + Vector((dx, 0.08, 0.02))
            L.spike(f"knuckle {lb}{k}", fa, b, b + d * 0.10 + Vector((0, 0.04, 0)), 0.035, "trim", sides=4)

    # ----- 骨盆：髋管 + 腰带 + 前后殓布 -----
    L.tube("hips", "Pelvis", [(0, 0, 1.08), (0, 0, 1.22), (0, 0, 1.36)], [(0.30, 0.38), (0.34, 0.44), (0.32, 0.40)], "armor",
           n=6, up=(0, 1, 0), twist=math.pi / 6, sharp=35)
    L.ring("belt", "Pelvis", (0, 0, 1.30), (0, 0, 1), 0.45, 0.035, "armor", count=8, n=3, squash=0.8)
    L.strip("loin front", "Pelvis", (0, 0.34, 1.26), (0, 0.25, -1), (1, 0, 0), 0.30, 0.55, jag=(0.8, 1.0, 0.7), cup=0.03)
    L.strip("loin back", "Pelvis", (0, -0.34, 1.28), (0, -0.28, -1), (1, 0, 0), 0.40, 0.60, jag=(0.75, 1.0, 0.7, 0.9), cup=-0.03)

    # ----- 石柱腿 -----
    for side, lb in SIDES:
        hp, kn, an = L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"]
        th, sn = f"Thigh.{lb}", f"Shin.{lb}"
        L.tube(f"thigh {lb}", th, [hp, kn], [0.20, 0.16], "armor", n=6, sharp=35)
        L.box(f"thigh slab {lb}", th, hp.lerp(kn, 0.45) + Vector((side * 0.08, 0.14, 0)), (0.24, 0.10, 0.34), "armor",
              rot=Matrix.Rotation(-0.2, 3, "X"), taper=(0.85, 0.9))
        L.box(f"knee stone {lb}", sn, kn + Vector((0, 0.13, 0.02)), (0.22, 0.14, 0.20), "armor", taper=(0.7, 0.8))
        L.tube(f"shin {lb}", sn, [kn, an], [0.16, 0.14], "armor", n=6, sharp=35)
        L.wrap(f"greave {lb}", sn, kn.lerp(an, 0.15), kn.lerp(an, 0.9), 0.19, 0.17, (0, 1, 0), "armor", arc=2.4, nu=4, nv=2,
               thick=0.02)
        x = an.x
        L.box(f"foot {lb}", sn, (x, 0.08, 0.08), (0.34, 0.46, 0.16), "armor", taper=(0.85, 0.7), shift=(0, 0.02), bev=0.02)
        for k, dx in enumerate((-0.10, 0.0, 0.10)):
            L.spike(f"toe {lb}{k}", sn, (x + dx, 0.29, 0.05), (x + dx * 1.1, 0.40, 0.012), 0.04, "armor", sides=3)
    return L.finalize()


# ===== 动作 =====
REVIEW_POSE = ("Attack", 1)


def stand(rig, st):
    p = {}
    shift(p, st, z=-0.03)
    for lb in ("L", "R"):
        plant(rig, st, p, lb, (0, 0, 0), ((-1 if lb == "L" else 1) * 0.12, 1, 0))
    return p


def move(rig, st, t):
    """巨像沉步：每步重心大幅左右移、落地一沉，巨拳前后甩，背棺随之起伏。"""
    p = {}
    shift(p, st, z=-0.05 + 0.035 * math.cos(2 * (t - 1.9)) - 0.02 * max(0.0, math.cos(2 * t)) ** 6)
    p["Pelvis"] = R((Z, -0.07 * math.cos(t)), (Y, 0.08 * math.sin(t)))
    p["Chest"] = R((Z, 0.10 * math.cos(t)), (Y, -0.06 * math.sin(t)), (X, -0.02 - 0.02 * math.cos(2 * t)))
    p["Head"] = R((Z, -0.04 * math.cos(t)))
    for lb, sg in (("L", -1), ("R", 1)):
        p[f"UpperArm.{lb}"] = R((X, sg * 0.24 * math.cos(t)), (Y, sg * 0.04))
        p[f"Forearm.{lb}"] = R((X, 0.10 + 0.08 * math.sin(t + (0 if sg > 0 else math.pi))))
    steps(rig, st, p, t, stride=0.62, lift=0.18, stance=0.64, width=0.01, pole_out=0.1)
    return p


def slam_key(rig, st, stage):
    """双拳砸地：1 双拳高举过顶、后仰 / 2 砸到身前地面 / 3 压住震地。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=-0.02)
        p["Chest"] = R((X, 0.20))
        p["Head"] = R((X, -0.10))
        for lb, sg in (("L", -1), ("R", 1)):
            rig.aim(p, f"UpperArm.{lb}", (sg * 0.35, 0.20, 0.92))
            rig.aim(p, f"Forearm.{lb}", (-sg * 0.25, -0.25, 0.94))
        plant(rig, st, p, "L", (0, 0.06, 0), (-0.12, 1, 0))
        plant(rig, st, p, "R", (0, -0.06, 0), (0.12, 1, 0))
    else:
        f = stage == 3
        shift(p, st, z=-0.24 if not f else -0.26, y=0.10)
        p["Chest"] = R((X, -0.55 if not f else -0.58))
        p["Head"] = R((X, 0.35))
        for lb, sg in (("L", -1), ("R", 1)):
            rig.aim(p, f"UpperArm.{lb}", (sg * 0.25, 0.75, -0.62))
            rig.aim(p, f"Forearm.{lb}", (-sg * 0.10, 0.40, -0.91))
        plant(rig, st, p, "L", (-0.05, 0.10, 0), (-0.25, 1, 0))
        plant(rig, st, p, "R", (0.05, -0.10, 0), (0.25, 1, 0))
    return p


def animate(rig, st):
    rig.loop("Move", 24, lambda t: move(rig, st, t), step=1)
    k = [slam_key(rig, st, i) for i in range(4)]
    rig.keyed("Attack", [(1, k[0]), (9, k[1]), (13, k[2]), (17, k[3]), (24, k[0])])
