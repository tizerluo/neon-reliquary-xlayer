"""空壳仆从 Husk Thrall（mob-0）/ 仆从百夫长 Thrall Centurion（elite-0）。

佝偻人形：兜帽下独眼骨白面具、胸前外露的骨白肋笼与猩红心缝、驼背披肩上一排椎骨刺；左肩圆甲、左手长爪，
右肩两根骨刺、右前臂整条换成锈刃（剪影上左右明显不对称）。
精英：镀金鸡冠盔 + 尖刺光冠、加大的枪铁刃（白红刃口）、双肩重甲、背后破红披风（Cape 骨），Attack 为直线冲锋。

躯干按直立坐标建模，再用 Legion.xform 绕腰部前压 HUNCH 弧度成佝偻；头、手臂在压弯后的世界坐标里建模
（头仍平视前方、手臂自然下垂）。
"""

import math

from mathutils import Matrix, Vector

from chars._legion import SIDES, TAU, Legion, R, X, Y, Z, cap_rim, pivot, plant, section, shift, steps

SIZE = 1.2
DROP = 0.08
TORSO_P = [(0, -0.02, 0.96), (0, -0.015, 1.07), (0, -0.005, 1.20), (0, 0.0, 1.33), (0, 0.02, 1.44)]
TORSO_R = [(0.085, 0.115), (0.085, 0.12), (0.145, 0.19), (0.14, 0.205), (0.08, 0.125)]   # (前后, 左右)
WAIST = Vector((0, -0.01, 1.0))
HUNCH = 0.68
BLADE_D = Vector((0.05, 0.55, -0.83)).normalized()


def blade_frame():
    """刃面宽度方向：把 X 绕刃向转 -40°，刃面斜朝前上（俯视也读得出），刃口朝内下。"""
    w = Matrix.Rotation(math.radians(-40), 3, BLADE_D) @ Vector((1, 0, 0))
    return (w - BLADE_D * w.dot(BLADE_D)).normalized()


def build(ctx, elite=False):
    L = Legion(ctx, elite, size=SIZE)
    E = elite
    D = Matrix.Translation((0, 0, -DROP))          # 短腿：整个上身下移
    H = D @ pivot(WAIST, Matrix.Rotation(-HUNCH, 3, "X"))
    J = L.joint
    neck = H @ Vector((0, 0.03, 1.46))
    hc = neck + Vector((0, 0.10, 0.035))
    J("head", hc)
    for side, lb in SIDES:
        J(f"hip.{lb}", (side * 0.12, 0.0, 0.86 - DROP))
        J(f"knee.{lb}", (side * 0.13, 0.12, 0.44))
        J(f"ankle.{lb}", (side * 0.13, -0.01, 0.085))
        sh = J(f"shoulder.{lb}", H @ Vector((side * 0.235, 0.0, 1.39)))
        el = J(f"elbow.{lb}", sh + Vector((side * 0.055, 0.03, -0.28)))
        J(f"wrist.{lb}", el + (Vector((0.01, 0.12, -0.27)) if side < 0 else Vector((0.01, 0.14, -0.24))))
    # ----- 骨架（12 节；精英加 Cape） -----
    L.bone("Root", (0, 0, 0), (0, 0, 0.25))
    L.bone("Pelvis", (0, 0, 0.84 - DROP), (0, -0.01, 1.00 - DROP), "Root")
    L.bone("Chest", D @ WAIST, neck, "Pelvis")
    L.bone("Head", neck, neck + Vector((0, 0.12, 0.12)), "Chest")
    for side, lb in SIDES:
        L.bone(f"UpperArm.{lb}", L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], "Chest")
        L.bone(f"Forearm.{lb}", L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"], f"UpperArm.{lb}")
        L.bone(f"Thigh.{lb}", L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], "Pelvis")
        L.bone(f"Shin.{lb}", L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"], f"Thigh.{lb}")
    if E:
        L.bone("Cape", H @ Vector((0, -0.12, 1.40)), H @ Vector((0, -0.12, 1.40)) + Vector((0, -0.08, -0.45)), "Chest")
    L.translate["Pelvis"] = "_bob"

    # ----- 躯干（直立建模 → 前压）：长管 + 骨白肋笼 + 猩红心缝 + 驼背披肩 + 椎骨刺 -----
    L.xform = H
    L.tube("torso", "Chest", TORSO_P, TORSO_R, "armor", n=8, up=(0, 1, 0))
    for k, z in enumerate((1.12, 1.20, 1.28)):
        cy, dep, wid = section(TORSO_P, TORSO_R, z)
        for side, lb in SIDES:
            pts = [Vector((side * wid * 1.08 * math.sin(a), cy + dep * 1.10 * math.cos(a), z - 0.04 * a))
                   for a in (0.16, 0.62, 1.10, 1.58)]
            L.trim(f"rib {k}{lb}", "Chest", pts, 0.0135, "trim", n=4)
    cy, dep, _ = section(TORSO_P, TORSO_R, 1.19)
    L.tube("heart slit", "Chest", [(0, cy + dep * 0.95, 1.08), (0, cy + dep * 1.03, 1.19), (0, cy + dep * 0.97, 1.31)],
           [0.010, 0.018, 0.010], "glow", n=4, up=(0, 1, 0))
    mc, max_, mr, mth, mph = Vector((0, -0.01, 1.33)), Vector((0, -0.45, 0.9)), (0.26, 0.215, 0.165), 1.35, (1.3, TAU - 1.3)
    L.cap("mantle", "Chest", mc, max_, mr, "cloth", theta=mth, nu=9, nv=3, phi=mph)
    for k, (y, z, h) in enumerate(((-0.17, 1.16, 0.08), (-0.175, 1.25, 0.10), (-0.165, 1.34, 0.115), (-0.13, 1.42, 0.10))):
        L.spike(f"vertebra {k}", "Chest", (0, y + 0.03, z), (0, y - 0.06, z + h * 0.35), 0.026, "trim", sides=4,
                flat=0.6, bend=(0, -0.01, h * 0.25))
    L.xform = None
    rim = [H @ p for p in cap_rim(mc, max_, mr, mth, 8, phi=mph)]
    for k, i in enumerate((1, 2, 3, 5, 6, 7)):
        top = rim[i]
        L.strip(f"mantle rag {k}", "Chest", top, (top.x * 0.5, -0.22, -1), (1, 0, 0), 0.10, 0.22 + 0.07 * (k % 2),
                jag=((0.6, 1.0, 0.8) if k % 2 else (1.0, 0.75, 0.55)), nv=3, cup=-0.012)
    for side, lb in SIDES:
        L.cable(f"cable {lb}", "Chest", [H @ Vector((side * 0.07, -0.13, 1.28)), H @ Vector((side * 0.085, -0.11, 1.45)),
                                         hc + Vector((side * 0.05, -0.12, 0.03))], 0.022, "armor", per=4, n=5)
    L.tube("neck", "Chest", [H @ Vector((0, 0.0, 1.40)), hc + Vector((0, -0.03, -0.04))], [0.055, 0.045], "armor", n=6)

    # ----- 骨盆：髋管 + 腰绳 + 前裆甲 + 后摆破布 -----
    L.xform = D
    L.tube("hips", "Pelvis", [(0, -0.01, 0.78), (0, -0.01, 0.88), (0, -0.015, 0.99)],
           [(0.09, 0.13), (0.115, 0.165), (0.10, 0.145)], "armor", n=8, up=(0, 1, 0))
    L.ring("belt", "Pelvis", (0, -0.01, 0.925), (0, 0, 1), 0.172, 0.018, "cloth", count=10, n=3, squash=0.72)
    L.plate("fauld", "Pelvis", [(-0.045, 0), (0.045, 0), (0.035, -0.19), (0, -0.23), (-0.035, -0.19)], 0.014,
            "armor", origin=(0, 0.125, 0.93), xaxis=(1, 0, 0), yaxis=(0, -0.28, 0.96))
    for k, (x, ln, w, jag) in enumerate(((-0.09, 0.42, 0.09, (0.7, 1.0, 0.8)), (0.0, 0.52, 0.10, (0.9, 1.0, 0.6)),
                                         (0.095, 0.38, 0.085, (1.0, 0.7, 0.85)))):
        L.strip(f"back rag {k}", "Pelvis", (x, -0.125, 0.945), (x * 0.3, -0.30, -1), (1, 0, 0), w, ln, jag=jag,
                cup=-0.014, curl=-0.03)
    for side, lb in SIDES:
        L.strip(f"hip rag {lb}", "Pelvis", (side * 0.165, -0.02, 0.94), (side * 0.35, -0.1, -1), (0, 1, 0), 0.09, 0.30,
                jag=(0.8, 1.0, 0.65), cup=0.01)
    L.xform = None

    # ----- 头：兜帽（精英为鸡冠盔）+ 独眼骨白面具 -----
    if not E:
        # 垂向脑后的尖兜帽：冠顶被拉向后上方成一个布尖，下缘盖到后颈
        L.cap("hood", "Head", hc + Vector((0, -0.03, 0.0)), (0, -0.62, 0.78), (0.14, 0.155, 0.16), "cloth",
              theta=2.05, nu=9, nv=4, phi=(1.0, TAU - 1.0),
              shape=lambda p, th, ph: p + Vector((0, -0.05 * (1 - th / 2.05) ** 2.5, 0.10 * (1 - th / 2.05) ** 3)))
    mask_c = hc + Vector((0, 0.05, -0.015))
    mask_ax = Vector((0, 0.96, -0.22)).normalized()
    L.cap("mask", "Head", mask_c, mask_ax, (0.095, 0.118, 0.064), "trim", theta=1.25, nu=8, nv=3, fwd=(0, 0, 1),
          thick=0.012, shape=lambda p, th, ph: Vector((p.x, p.y * (1.35 if p.y < 0 else 1.0), p.z)))
    L.eye("eye", "Head", mask_c + mask_ax * 0.061 + Vector((0, 0, 0.02)), mask_ax, 0.036 if not E else 0.042)

    # ----- 手臂：左肩圆甲 + 长爪，右肩骨刺 + 锈刃前臂 -----
    for side, lb in SIDES:
        sh, el, wr = L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"]
        L.tube(f"upper arm {lb}", f"UpperArm.{lb}", [sh, el], [0.052, 0.040], "armor", n=6)
        if side < 0 or E:
            pc = sh + Vector((side * 0.02, -0.01, 0.035))
            pax = (side * 0.55, -0.1, 0.83)
            pr = (0.13, 0.12, 0.10) if not E else (0.15, 0.14, 0.12)
            L.cap(f"pauldron {lb}", "Chest", pc, pax, pr, "armor", theta=1.35, nu=8, nv=3, thick=0.014)
            L.trim(f"pauldron rim {lb}", "Chest", cap_rim(pc, pax, pr, 1.35, 8, grow=0.004), 0.008, "trim",
                   n=3, closed=True)
            if E:
                top = pc + Vector(pax).normalized() * pr[2]
                L.spike(f"pauldron spike {lb}", "Chest", top, top + Vector((side * 0.06, -0.02, 0.15)), 0.03, "trim",
                        sides=4)
        else:
            L.cap("shoulder cap R", "Chest", sh + Vector((0, 0, 0.02)), (0.5, 0, 0.86), (0.08, 0.08, 0.07),
                  "armor", theta=1.2, nu=6, nv=2, thick=0.01)
            b0 = sh + Vector((-0.02, -0.03, 0.03))
            L.spike("shoulder bone 0", "Chest", b0, b0 + Vector((0.08, -0.07, 0.24)), 0.032, "trim", sides=4,
                    bend=(0.025, 0, 0))
            b1 = sh + Vector((-0.07, -0.08, 0.04))
            L.spike("shoulder bone 1", "Chest", b1, b1 + Vector((0.03, -0.10, 0.18)), 0.025, "trim", sides=4)
        if lb == "L":
            L.tube("forearm L", "Forearm.L", [el, wr], [0.042, 0.032], "armor", n=6)
            L.wrap("vambrace L", "Forearm.L", el.lerp(wr, 0.15), el.lerp(wr, 0.85), 0.054, 0.046, (-1, 0.2, 0),
                   "armor", arc=2.4, nu=4, nv=2, thick=0.01)
            d = (wr - el).normalized()
            palm = wr + d * 0.035
            L.ell("claw palm", "Forearm.L", palm, (0.036, 0.04, 0.045), "armor", 6, 4)
            for k, (dx, dy) in enumerate(((-0.032, 0.015), (0.0, 0.035), (0.032, 0.02))):
                base = palm + Vector((dx, dy, -0.02))
                L.spike(f"claw {k}", "Forearm.L", base, base + d * 0.16 + Vector((dx * 0.7, 0.04, 0)), 0.014, "armor",
                        sides=3, bend=(0, 0.04, 0))
    # 右前臂：锈刃（精英为加大的枪铁刃 + 白红刃口 + 金刃脊）
    el, wr = L.J["elbow.R"], L.J["wrist.R"]
    L.tube("gauntlet R", "Forearm.R", [el, wr + BLADE_D * 0.04], [0.050, 0.062], "armor", n=6)
    L.ring("gauntlet cuff R", "Forearm.R", wr + BLADE_D * 0.035, BLADE_D, 0.064, 0.011, "armor", count=6, n=3)
    wdir = blade_frame()
    k, kw = (1.2, 1.35) if E else (1.0, 1.0)
    outline = [(-0.02, 0.035), (0.30, 0.042), (0.52, 0.032), (0.64, -0.005), (0.51, -0.078), (0.40, -0.095),
               (0.345, -0.074), (0.30, -0.090), (0.18, -0.074), (0.14, -0.053), (0.10, -0.067), (-0.02, -0.045)]
    outline = [(x * k, y * kw) for x, y in outline]
    origin = wr + BLADE_D * 0.02
    L.plate("blade", "Forearm.R", outline, 0.016, "armor" if E else "cloth", origin, BLADE_D, wdir)
    edge = [(0.62, -0.02), (0.51, -0.082), (0.40, -0.099), (0.30, -0.094), (0.18, -0.078), (0.10, -0.071)]
    L.trim("blade edge", "Forearm.R", [origin + BLADE_D * (x * k) + wdir * (y * kw) for x, y in edge],
           0.0065, "glow" if E else "armor", n=3)
    if E:
        spine = [(0.0, 0.040), (0.30, 0.047), (0.52, 0.036)]
        L.trim("blade spine", "Forearm.R", [origin + BLADE_D * (x * k) + wdir * (y * kw) for x, y in spine], 0.009,
               "trim", n=3)

    # ----- 腿：细瘦枪铁腿 + 大护膝 + 爪靴 -----
    for side, lb in SIDES:
        hp, kn, an = L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"]
        th, sh = f"Thigh.{lb}", f"Shin.{lb}"
        L.tube(f"thigh {lb}", th, [hp, kn], [0.068, 0.050], "armor", n=6)
        L.wrap(f"cuisse {lb}", th, hp.lerp(kn, 0.1), hp.lerp(kn, 0.8), 0.084, 0.066, (side * 0.8, 0.6, 0), "armor",
               arc=2.2, nu=4, nv=2, thick=0.012)
        L.cap(f"knee {lb}", sh, kn + Vector((0, 0.03, 0.0)), (0, 1, 0.25), (0.064, 0.064, 0.052), "armor", theta=1.2,
              nu=6, nv=2, thick=0.01)
        L.spike(f"knee spike {lb}", sh, kn + Vector((0, 0.07, 0.01)), kn + Vector((side * 0.01, 0.15, 0.06)), 0.022,
                "armor", sides=3)
        L.tube(f"shin {lb}", sh, [kn, an], [0.048, 0.037], "armor", n=6)
        L.wrap(f"greave {lb}", sh, kn.lerp(an, 0.12), kn.lerp(an, 0.88), 0.062, 0.050, (0, 1, 0), "armor", arc=2.4,
               nu=4, nv=2, thick=0.01)
        x = an.x
        L.tube(f"foot {lb}", sh, [(x, -0.08, 0.05), (x, 0.03, 0.05), (x, 0.16, 0.028)],
               [(0.07, 0.050), (0.07, 0.056), (0.035, 0.034)], "armor", n=4, up=(0, 0, 1), twist=math.pi / 4)
        for dx in (-0.022, 0.022):
            L.spike(f"toe claw {lb}{dx:+.3f}", sh, (x + dx, 0.14, 0.022), (x + dx * 1.3, 0.23, 0.006), 0.014, "armor",
                    sides=3)

    if E:
        build_centurion(L, H, hc)
    return L.finalize(blade_w=wdir)


def build_centurion(L, H, hc):
    """精英升格件：镀金鸡冠盔、尖刺光冠、白红胸核 + 金胸板、破红披风。"""
    helm_c, helm_ax, helm_r, helm_th, helm_ph = hc + Vector((0, -0.01, 0.005)), (0, -0.15, 1), (0.134, 0.150, 0.137), 1.78, (0.85, TAU - 0.85)
    L.cap("helm", "Head", helm_c, helm_ax, helm_r, "armor", theta=helm_th, nu=10, nv=3, phi=helm_ph, thick=0.012)
    L.trim("helm brow", "Head", cap_rim(helm_c, helm_ax, helm_r, helm_th, 10, phi=helm_ph, grow=0.004), 0.009, "trim", n=3)
    comb = [(0.11, 0.07), (0.075, 0.19), (0.0, 0.265), (-0.10, 0.25), (-0.19, 0.17), (-0.21, 0.07), (-0.14, 0.10),
            (-0.05, 0.135), (0.05, 0.12)]
    L.plate("crest", "Head", comb, 0.024, "trim", origin=hc + Vector((0, 0, 0.02)), xaxis=(0, 1, 0), yaxis=(0, 0, 1))
    L.halo_crown("halo crown", "Head", hc + Vector((0, -0.12, 0.08)), (0, -0.6, 0.8), 0.20, spikes=9, length=0.09,
                 r=0.009, tilt=0.35)
    L.xform = H
    cy, dep, _ = section(TORSO_P, TORSO_R, 1.21)
    L.gem("core", "Chest", (0, cy + dep * 1.02, 1.21), 0.045, "glow", stretch=(0.8, 0.5, 1.2), sides=4)
    for side in (-1, 1):
        L.plate(f"sternum plate {side}", "Chest", [(0, 0.08), (0.07, 0.03), (0.06, -0.09), (0.0, -0.12)], 0.012, "trim",
                origin=(side * 0.035, cy + dep * 1.06, 1.20), xaxis=(side, 0.35, 0), yaxis=(0, 0, 1))
    L.xform = None
    top = H @ Vector((0, -0.10, 1.43))

    def cape(u, v):
        c = (u - 0.5) * 2
        jag = (1.0, 0.78, 0.96, 0.7, 0.92, 0.82)[min(5, int(u * 5.999))]
        ln = 0.95 * (1 - (1 - jag) * v ** 3)
        w = 0.25 + 0.13 * v
        return Vector((c * w, top.y - 0.10 * (1 - c * c) - 0.12 * v - 0.06 * v * v, top.z - v * ln))
    L.surf("cape", "Cape", cape, 6, 4, "cloth", ref=lambda q: Vector((0, top.y + 0.2, q.z)))
    for side in (-1, 1):
        L.gem(f"cape clasp {side}", "Chest", (side * 0.20, top.y + 0.02, top.z - 0.01), 0.03, "trim",
              stretch=(1, 0.6, 1), sides=4)


# ===== 动作 =====
REVIEW_POSE = ("Attack", 1)


def stand(rig, st, crouch=0.0):
    p = {}
    shift(p, st, z=-0.02 - crouch)
    p["Chest"] = R((X, -0.02))
    p["UpperArm.L"] = R((X, 0.05))
    p["Forearm.L"] = R((X, 0.10))
    for lb in ("L", "R"):
        plant(rig, st, p, lb, (0, 0, 0), ((-1 if lb == "L" else 1) * 0.15, 1, 0))
    if st["elite"]:
        p["Cape"] = R((X, -0.06))
    return p


def move(rig, st, t):
    """蹒跚前行：骨盆随迈步扭转、上身左右晃、驼背一耸一耸；锈刃沉重地小幅摆动。"""
    p = {}
    shift(p, st, z=-0.035 + 0.022 * math.cos(2 * (t - 1.75)))
    p["Pelvis"] = R((Z, -0.10 * math.cos(t)), (Y, 0.05 * math.sin(t)))
    p["Chest"] = R((X, -(0.04 + 0.04 * math.cos(2 * t))), (Z, 0.15 * math.cos(t)), (Y, -0.08 * math.sin(t)))
    p["Head"] = R((X, 0.05 + 0.03 * math.cos(2 * t)), (Z, -0.10 * math.cos(t + 0.3)))
    p["UpperArm.L"] = R((X, -0.36 * math.cos(t)), (Y, -0.05))
    p["Forearm.L"] = R((X, 0.20 + 0.14 * math.sin(t)))
    p["UpperArm.R"] = R((X, 0.12 * math.cos(t)))
    p["Forearm.R"] = R((X, 0.04 + 0.04 * math.sin(t)))
    steps(rig, st, p, t, stride=0.34, lift=0.10, stance=0.6, pole_out=0.15)
    if st["elite"]:
        p["Cape"] = R((X, -0.14 - 0.05 * math.cos(2 * t)), (Y, 0.05 * math.sin(t)))
    return p


def blade_aim(rig, st, p, d, w):
    """前臂刃指向 d，刃宽方向转到 w（刃口 = -w 领先挥砍方向，刃面朝镜头）。"""
    rig.aim(p, "Forearm.R", d, up=w, rest_up=st["blade_w"])


def slash_key(rig, st, stage):
    """斜劈：0 静止 / 1 右拧后引举刃 / 2 刃越过右前上方 / 3 劈到左前下方 / 4 顺势收刀。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=-0.05)
        p["Pelvis"] = R((Z, -0.18))
        p["Chest"] = R((Z, -0.40), (X, 0.14))
        p["Head"] = R((Z, 0.25), (X, 0.04))
        rig.aim(p, "UpperArm.R", (0.55, -0.35, 0.75))
        blade_aim(rig, st, p, (0.25, -0.30, 0.92), (0.0, -1.0, 0.3))
        rig.aim(p, "UpperArm.L", (-0.30, 0.75, -0.55))
        rig.aim(p, "Forearm.L", (-0.10, 0.90, -0.20))
        plant(rig, st, p, "L", (0, 0.0, 0), (-0.15, 1, 0))
        plant(rig, st, p, "R", (0.02, -0.06, 0), (0.15, 1, 0))
    elif stage == 2:
        shift(p, st, z=-0.07, y=0.02)
        p["Pelvis"] = R((Z, 0.02))
        p["Chest"] = R((Z, 0.05), (X, -0.08))
        p["Head"] = R((Z, -0.04), (X, 0.10))
        rig.aim(p, "UpperArm.R", (0.45, 0.55, 0.55))
        blade_aim(rig, st, p, (0.30, 0.80, 0.50), (0.6, -0.1, -0.8))
        rig.aim(p, "UpperArm.L", (-0.35, 0.20, -0.90))
        rig.aim(p, "Forearm.L", (-0.20, 0.30, -0.90))
        plant(rig, st, p, "L", (-0.01, 0.06, 0), (-0.15, 1, 0))
        plant(rig, st, p, "R", (0.02, -0.06, 0), (0.15, 1, 0))
    else:
        f = stage == 4
        shift(p, st, z=-0.10, y=0.05)
        p["Pelvis"] = R((Z, 0.20 if not f else 0.26), (X, 0.08))
        p["Chest"] = R((Z, 0.42 if not f else 0.52), (X, -0.24 if not f else -0.30))
        p["Head"] = R((Z, -0.30), (X, 0.20))
        rig.aim(p, "UpperArm.R", (-0.20, 0.85, -0.50) if not f else (-0.40, 0.65, -0.65))
        blade_aim(rig, st, p, (-0.50, 0.55, -0.67) if not f else (-0.72, 0.20, -0.66), (1.0, 0.0, 0.5))
        rig.aim(p, "UpperArm.L", (-0.35, -0.45, -0.80))
        rig.aim(p, "Forearm.L", (-0.20, -0.30, -0.90))
        plant(rig, st, p, "L", (-0.01, 0.12, 0), (-0.15, 1, 0))
        plant(rig, st, p, "R", (0.02, -0.06, 0), (0.15, 1, 0))
    if st["elite"]:
        p["Cape"] = R((X, -0.10 - 0.10 * stage))
    return p


def charge_key(rig, st, stage):
    """精英直线冲锋：1 蓄势下蹲 / 2、3 前倾狂奔（刃平举前刺，两脚交替）。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=-0.11, y=-0.03)
        p["Pelvis"] = R((X, 0.12))
        p["Chest"] = R((X, -0.20), (Z, -0.12))
        p["Head"] = R((X, 0.22))
        rig.aim(p, "UpperArm.R", (0.45, -0.55, -0.55))
        blade_aim(rig, st, p, (0.20, 0.35, -0.90), (1.0, 0.0, 0.3))
        rig.aim(p, "UpperArm.L", (-0.30, 0.60, -0.70))
        rig.aim(p, "Forearm.L", (-0.10, 0.85, -0.40))
        plant(rig, st, p, "L", (0, 0.14, 0), (-0.15, 1, 0))
        plant(rig, st, p, "R", (0, -0.16, 0), (0.15, 1, 0))
        p["Cape"] = R((X, -0.25))
        return p
    a = 1 if stage == 2 else -1
    shift(p, st, z=-0.06, y=0.06)
    p["Pelvis"] = R((X, 0.18), (Z, 0.08 * a))
    p["Chest"] = R((X, -0.30), (Z, -0.10 * a))
    p["Head"] = R((X, 0.30))
    rig.aim(p, "UpperArm.R", (0.18, 0.92, -0.25))
    blade_aim(rig, st, p, (0.02, 1.0, 0.02), (1.0, 0.0, 0.0))
    rig.aim(p, "UpperArm.L", (-0.30, -0.50 * a + 0.1, -0.80))
    rig.aim(p, "Forearm.L", (-0.20, 0.30 - 0.3 * a, -0.85))
    plant(rig, st, p, "L", (0, 0.24 * a, 0.10 * max(0, -a)), (-0.15, 1, 0))
    plant(rig, st, p, "R", (0, -0.24 * a, 0.10 * max(0, a)), (0.15, 1, 0))
    p["Cape"] = R((X, -0.72 - 0.08 * a), (Y, 0.06 * a))
    return p


def animate(rig, st):
    rig.loop("Move", 20, lambda t: move(rig, st, t), step=1)
    if st["elite"]:
        k = [charge_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (6, k[1]), (9, k[2]), (13, k[3]), (17, k[2]), (21, k[3]), (24, k[0])])
    else:
        k = [slash_key(rig, st, i) for i in range(5)]
        rig.keyed("Attack", [(1, k[0]), (7, k[1]), (9, k[2]), (11, k[3]), (14, k[4]), (20, k[0])])
