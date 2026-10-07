"""咒唱司铎 Hex Cantor（mob-6，无精英）。

悬浮的长袍祭司机：没有腿，枪铁法衣分上袍（Body）与下摆（Hem，漂移时向后滞摆）两节，下摆破成一圈垂片，
袍底一圈紫色浮游光；高立领披肩 + 骨白滚边，尖顶兜帽下骨白面具一道弯月形猩红光缝；宽袖双臂——右手竖握
比自身还高的法杖，杖首弯钩上吊着一盏提灯（骨白笼架 + 紫色 #d995ff 灯芯，挂 Lantern 骨，随动作摆荡），
左手前伸结印，掌前浮着一枚紫色符环。俯视：杖顶一点紫光 + 掌前紫环 + 圆袍。
远程单位 4 种材质：枪铁（兼作法衣）、骨白、猩红感光、紫色武器光。骨架 10 节。
"""

import math

from mathutils import Matrix, Vector

from chars._legion import SIDES, TAU, VIOLET, Legion, R, X, Y, Z, cap_rim

SIZE = 0.92


def build(ctx, elite=False):
    L = Legion(ctx, elite, weapon=("hex violet glow", VIOLET), size=SIZE)
    J = L.joint
    for side, lb in SIDES:
        J(f"shoulder.{lb}", (side * 0.22, 0.02, 1.44))
    J("elbow.R", (0.30, 0.10, 1.20))
    J("wrist.R", (0.32, 0.27, 1.13))
    J("elbow.L", (-0.31, 0.20, 1.24))
    J("wrist.L", (-0.22, 0.43, 1.31))
    hook = Vector((0.33, 0.40, 2.12))
    L.bone("Root", (0, 0, 0), (0, 0, 0.25))
    L.bone("Body", (0, 0, 0.70), (0, 0, 1.08), "Root")
    L.bone("Hem", (0, 0, 0.66), (0, -0.02, 0.28), "Body")
    L.bone("Chest", (0, 0, 1.08), (0, 0.04, 1.52), "Body")
    L.bone("Head", (0, 0.05, 1.52), (0, 0.08, 1.78), "Chest")
    for lb in ("L", "R"):
        L.bone(f"UpperArm.{lb}", L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], "Chest")
        L.bone(f"Forearm.{lb}", L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"], f"UpperArm.{lb}")
    L.bone("Lantern", hook, hook + Vector((0, 0, -0.30)), "Forearm.R")
    L.translate["Body"] = "_bob"

    # ----- 法衣：上袍（Body）+ 下摆（Hem）+ 破垂片 + 紫色浮游光 -----
    L.tube("robe", "Body", [(0, 0.0, 1.12), (0, -0.005, 0.95), (0, -0.01, 0.74), (0, -0.015, 0.54)],
           [(0.15, 0.18), (0.19, 0.22), (0.24, 0.26), (0.27, 0.29)], "armor", n=10, up=(0, 1, 0), cap=False, sharp=20)
    L.tube("hem", "Hem", [(0, -0.015, 0.64), (0, -0.02, 0.46), (0, -0.03, 0.30)], [(0.24, 0.26), (0.30, 0.32), (0.34, 0.36)],
           "armor", n=10, up=(0, 1, 0), cap=False, sharp=20)
    L.ring("hem band", "Hem", (0, -0.03, 0.305), (0, 0, 1), 0.355, 0.015, "trim", count=12, n=3, squash=0.95)
    L.ring("waist band", "Body", (0, 0.0, 1.02), (0, 0, 1), 0.205, 0.018, "trim", count=10, n=3, squash=0.85)
    L.tube("front band", "Body", [(0, 0.20, 1.00), (0, 0.255, 0.76), (0, 0.29, 0.56)], [(0.008, 0.045)] * 3, "trim", n=4,
           up=(0, 1, 0))
    for k in range(9):
        a = TAU * (k + 0.5) / 9
        top = Vector((math.sin(a) * 0.35, -0.03 + math.cos(a) * 0.33, 0.31))
        L.strip(f"hem tatter {k}", "Hem", top, (math.sin(a) * 0.25, math.cos(a) * 0.25, -1), (math.cos(a), -math.sin(a), 0),
                0.12, 0.13 + 0.06 * (k % 3 == 1), jag=((0.6, 1.0, 0.7) if k % 2 else (1.0, 0.6, 0.85)), nv=2, mat="cloth")
    L.ring("levitation glow", "Hem", (0, -0.03, 0.27), (0, 0, 1), 0.20, 0.018, "weapon", count=10, n=3)

    # ----- 上身：躯干 + 高立领披肩 + 垂祷条 -----
    L.tube("torso", "Chest", [(0, 0.0, 1.06), (0, 0.02, 1.26), (0, 0.04, 1.44), (0, 0.05, 1.53)],
           [(0.13, 0.16), (0.14, 0.20), (0.13, 0.21), (0.07, 0.11)], "armor", n=8, up=(0, 1, 0))
    mc, max_, mr, mth, mph = Vector((0, 0.03, 1.44)), (0, -0.15, 1), (0.30, 0.25, 0.13), 1.5, (0.75, TAU - 0.75)
    L.cap("mantle", "Chest", mc, max_, mr, "armor", theta=mth, nu=10, nv=3, phi=mph, thick=0.012)
    L.trim("mantle rim", "Chest", cap_rim(mc, max_, mr, mth, 10, phi=mph, grow=0.004), 0.011, "trim", n=3)
    # 高立领：身后一片弧形立板，顶缘骨白
    def collar(u, v):
        a = math.pi + (u - 0.5) * 2.4
        r = 0.20 + 0.05 * v
        return Vector((math.sin(a) * r, 0.04 + math.cos(a) * r * 0.8, 1.48 + 0.30 * v - 0.05 * (u - 0.5) ** 2))
    L.surf("high collar", "Chest", collar, 6, 2, "armor", ref=lambda q: Vector((0, 0.06, q.z)), thick=0.012)
    L.trim("collar rim", "Chest", [collar(i / 6, 1.0) + Vector((0, 0, 0.005)) for i in range(7)], 0.012, "trim", n=3)
    for k, (x, ln) in enumerate(((-0.12, 0.42), (0.12, 0.36))):
        L.strip(f"prayer strip {k}", "Chest", (x, 0.25, 1.38), (x * 0.1, 0.1, -1), (1, 0, 0), 0.06, ln, jag=(0.8, 1.0, 0.7),
                nv=3, mat="trim")

    # ----- 头：尖兜帽 + 骨白面具 + 弯月光缝 -----
    hc = Vector((0, 0.08, 1.64))
    L.cap("hood", "Head", hc + Vector((0, -0.02, 0)), (0, -0.2, 1), (0.13, 0.145, 0.15), "armor", theta=1.9, nu=9, nv=3,
          phi=(0.85, TAU - 0.85), thick=0.01,
          shape=lambda p, th, ph: p + Vector((0, -0.05 * (1 - th / 1.9) ** 2, 0.16 * (1 - th / 1.9) ** 3)))
    mask_c, mask_ax = hc + Vector((0, 0.045, -0.01)), Vector((0, 0.98, -0.12)).normalized()
    L.cap("mask", "Head", mask_c, mask_ax, (0.078, 0.10, 0.05), "trim", theta=1.2, nu=8, nv=2, fwd=(0, 0, 1), thick=0.01)
    face = mask_c + mask_ax * 0.05
    L.tube("crescent slit", "Head", [face + Vector((x, 0.004 - abs(x) * 0.5, 0.012 + 0.9 * x * x)) for x in (-0.045, -0.02, 0.0, 0.02, 0.045)],
           [0.006, 0.009, 0.010, 0.009, 0.006], "glow", n=4)

    # ----- 宽袖双臂 -----
    for lb in ("L", "R"):
        sh, el, wr = L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"]
        L.tube(f"upper arm {lb}", f"UpperArm.{lb}", [sh, el], [0.05, 0.042], "armor", n=6)
        d = (wr - el).normalized()
        L.tube(f"sleeve {lb}", f"Forearm.{lb}", [el - d * 0.02, wr - d * 0.02], [0.06, 0.10], "armor", n=8, cap=False,
               sharp=25)
        L.ring(f"cuff {lb}", f"Forearm.{lb}", wr - d * 0.02, d, 0.10, 0.011, "trim" if lb == "R" else "armor", count=8, n=3)
        L.ell(f"hand {lb}", f"Forearm.{lb}", wr + d * 0.04, (0.04, 0.045, 0.05), "armor", 6, 4)
    # 左掌前浮着的紫色符环 + 三枚光点
    wl, dl = L.J["wrist.L"], (L.J["wrist.L"] - L.J["elbow.L"]).normalized()
    gc = wl + dl * 0.16
    L.ring("hex glyph", "Forearm.L", gc, dl, 0.085, 0.009, "weapon", count=10, n=3, fwd=(0, 0, 1))
    for k in range(3):
        a = TAU * k / 3
        L.gem(f"glyph mote {k}", "Forearm.L", gc + Matrix.Rotation(a, 3, dl) @ Vector((0, 0, 0.05)), 0.013, "weapon", sides=4)

    # ----- 法杖（右前臂）+ 弯钩 -----
    g = L.J["wrist.R"] + Vector((0.01, 0.05, 0.0))
    base, top = Vector((g.x, g.y - 0.005, 0.62)), Vector((g.x + 0.005, g.y + 0.04, 2.05))
    L.tube("staff", "Forearm.R", [base, top], [0.02, 0.026], "armor", n=5)
    L.spike("staff heel", "Forearm.R", base + Vector((0, 0, 0.02)), base + Vector((0, 0, -0.12)), 0.024, "trim", sides=4)
    for k, z in enumerate((0.95, 1.30, 1.85)):
        L.ring(f"staff band {k}", "Forearm.R", base.lerp(top, (z - base.z) / (top.z - base.z)), top - base, 0.032, 0.01, "trim",
               count=6, n=3)
    crook = [top, top + Vector((0, 0.02, 0.09)), top + Vector((0, 0.08, 0.14)), hook + Vector((0, 0, 0.03)), hook]
    L.tube("staff crook", "Forearm.R", crook, [0.026, 0.024, 0.02, 0.016, 0.012], "trim", n=5)
    L.spike("staff finial", "Forearm.R", top + Vector((0, 0.0, 0.10)), top + Vector((0, -0.03, 0.26)), 0.022, "trim", sides=4)

    # ----- 提灯（Lantern 骨）：短链 + 骨白笼架 + 紫色灯芯 -----
    lc = hook + Vector((0, 0, -0.20))
    L.chain("lantern chain", "Lantern", [hook, lc + Vector((0, 0, 0.10))], "armor", link=0.05, wire=0.007, width=0.028, lean=True)
    L.ell("lantern core", "Lantern", lc, (0.058, 0.058, 0.085), "weapon", 8, 5)
    L.ell("lantern cap", "Lantern", lc + Vector((0, 0, 0.095)), (0.07, 0.07, 0.03), "armor", 8, 3)
    L.ell("lantern base", "Lantern", lc + Vector((0, 0, -0.095)), (0.06, 0.06, 0.025), "armor", 8, 3)
    L.spike("lantern drop", "Lantern", lc + Vector((0, 0, -0.11)), lc + Vector((0, 0, -0.19)), 0.02, "trim", sides=4)
    for k in range(4):
        a = TAU * (k + 0.5) / 4
        o = Vector((math.sin(a) * 0.06, math.cos(a) * 0.06, 0))
        L.trim(f"lantern bar {k}", "Lantern", [lc + o + Vector((0, 0, 0.09)), lc + o * 1.35, lc + o + Vector((0, 0, -0.09))],
               0.006, "trim", n=3)
    return L.finalize(hook=hook)


# ===== 动作 =====
REVIEW_POSE = ("Attack", 1)


def move(rig, st, t):
    """悬浮漂移：整体上下浮动、上身前倾，下摆向后滞摆，提灯钟摆式晃动。"""
    p = {}
    s = st["s"]
    p["_bob"] = Vector((0, 0, (0.035 * math.sin(t)) * s))
    p["Body"] = R((X, -0.08 + 0.02 * math.sin(t + 0.6)), (Y, 0.03 * math.sin(t)))
    p["Hem"] = R((X, -0.16 - 0.05 * math.sin(t - 0.8)), (Y, 0.05 * math.sin(t - 1.0)))
    p["Chest"] = R((X, -0.02), (Z, 0.03 * math.sin(t)))
    p["Head"] = R((X, 0.06), (Z, -0.04 * math.sin(t)))
    p["UpperArm.R"] = R((X, 0.04 * math.sin(t)))
    p["UpperArm.L"] = R((X, 0.05 * math.sin(t + 1.0)))
    p["Forearm.L"] = R((X, 0.04 * math.sin(t + 1.5)))
    p["Lantern"] = R((X, 0.28 + 0.12 * math.sin(t - 1.4)), (Y, 0.06 * math.sin(t)))
    return p


def idle_pose(st):
    p = {}
    p["_bob"] = Vector((0, 0, 0))
    p["Hem"] = R((X, -0.03))
    return p


def cast_key(rig, st, stage):
    """咒唱：1 高举法杖、提灯后荡、左手收回 / 2 法杖前劈、提灯甩向前方、左掌推出 / 3 收势。"""
    if stage == 0:
        return idle_pose(st)
    s = st["s"]
    p = {}
    if stage == 1:
        p["_bob"] = Vector((0, 0, 0.10 * s))
        p["Body"] = R((X, 0.10))
        p["Hem"] = R((X, 0.12))
        p["Chest"] = R((X, 0.10), (Z, -0.10))
        p["Head"] = R((X, 0.12))
        # 法杖与前臂夹角固定约 112°：前臂仍前下指、整条手臂抬高，杖才会竖直高举
        rig.aim(p, "UpperArm.R", (0.55, 0.15, 0.82))
        rig.aim(p, "Forearm.R", (0.08, 0.90, -0.42), up=(0, -0.2, 1), rest_up=(0, 0, 1))
        rig.aim(p, "UpperArm.L", (-0.60, -0.10, -0.80))
        rig.aim(p, "Forearm.L", (-0.20, 0.40, 0.89))
        p["Lantern"] = R((X, -0.55))
    else:
        k = 1.0 if stage == 2 else 0.6
        p["_bob"] = Vector((0, 0.06 * s * k, 0.02 * s))
        p["Body"] = R((X, -0.14 * k))
        p["Hem"] = R((X, -0.26 * k))
        p["Chest"] = R((X, -0.12 * k), (Z, 0.08 * k))
        p["Head"] = R((X, 0.02))
        rig.aim(p, "UpperArm.R", (0.30, 0.90, 0.10 - 0.15 * (1 - k)))
        rig.aim(p, "Forearm.R", (0.05, 0.30 + 0.4 * (1 - k), -0.95), up=(0.02, 0.88 * k, 0.38 + 0.6 * (1 - k)),
                rest_up=(0, 0, 1))
        rig.aim(p, "UpperArm.L", (-0.30, 0.85, 0.05))
        rig.aim(p, "Forearm.L", (-0.05, 1.0, 0.10))
        p["Lantern"] = R((X, 0.75 * k))
    return p


def animate(rig, st):
    rig.loop("Move", 24, lambda t: move(rig, st, t), step=1)
    k = [cast_key(rig, st, i) for i in range(4)]
    rig.keyed("Attack", [(1, k[0]), (8, k[1]), (12, k[2]), (16, k[3]), (22, k[0])])
