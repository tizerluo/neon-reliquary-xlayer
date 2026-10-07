"""帷影刺客 Veil Stalker（mob-3）/ 帷影处刑者 Veil Executioner（elite-3）。

细长的前倾猎手：高耸尖兜帽下骨白面具上三点猩红感光（三角排布），下半张脸垂着破帷布条；窄腰细躯，
反关节长腿（大腿前伸、胫部后折、跖骨前落，刚性挂在 Shin 骨上），双前臂各接一条 0.75 m 的骨白长刃；
腰后三条长破布燕尾挂 Tails 骨（奔跑时向后扬起）。俯视：两条白刃 + 尖兜帽 + 身后布尾。
精英：放大 1.3 倍，金面具、尖刺光冠、金边尖肩甲，双刃换成新月形长镰（金脊 + 白红刃口），红色长燕尾；
Attack 为跃起双镰砸地（地面范围圈）。骨架 13 节。
"""

import math

from mathutils import Matrix, Vector

from chars._legion import SIDES, TAU, Legion, R, X, Y, Z, cap_rim, pivot, plant, section, shift, steps

SIZE = 1.065
TORSO_P = [(0, 0.0, 0.98), (0, 0.0, 1.08), (0, 0.01, 1.22), (0, 0.01, 1.36), (0, 0.0, 1.46)]
TORSO_R = [(0.09, 0.12), (0.075, 0.105), (0.12, 0.17), (0.12, 0.19), (0.07, 0.11)]
WAIST = Vector((0, 0.0, 1.0))
LEAN = 0.30


def blade_axes(side, d):
    """刃面：含刃向 d，宽度方向把 X 绕 d 转 ∓35°（刃面斜朝上，俯视读得出），刃口朝外下。"""
    w = Matrix.Rotation(math.radians(-35 * side), 3, d) @ Vector((side, 0, 0))
    return (w - d * w.dot(d)).normalized()


def build(ctx, elite=False):
    L = Legion(ctx, elite, size=SIZE)
    E = elite
    H = pivot(WAIST, Matrix.Rotation(-LEAN, 3, "X"))
    J = L.joint
    neck = H @ Vector((0, 0.01, 1.47))
    hc = neck + Vector((0, 0.06, 0.10))
    for side, lb in SIDES:
        J(f"hip.{lb}", (side * 0.10, 0.0, 0.98))
        J(f"knee.{lb}", (side * 0.115, 0.19, 0.66))
        J(f"ankle.{lb}", (side * 0.115, 0.03, 0.05))
        sh = J(f"shoulder.{lb}", H @ Vector((side * 0.19, -0.01, 1.42)))
        el = J(f"elbow.{lb}", sh + Vector((side * 0.06, -0.02, -0.27)))
        J(f"wrist.{lb}", el + Vector((side * 0.01, 0.16, -0.20)))
    L.bone("Root", (0, 0, 0), (0, 0, 0.25))
    L.bone("Pelvis", (0, 0, 0.94), (0, 0, 1.02), "Root")
    L.bone("Chest", WAIST, neck, "Pelvis")
    L.bone("Head", neck, neck + Vector((0, 0.05, 0.16)), "Chest")
    L.bone("Tails", (0, -0.10, 1.02), (0, -0.20, 0.55), "Pelvis")
    for side, lb in SIDES:
        L.bone(f"UpperArm.{lb}", L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], "Chest")
        L.bone(f"Forearm.{lb}", L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"], f"UpperArm.{lb}")
        L.bone(f"Thigh.{lb}", L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], "Pelvis")
        L.bone(f"Shin.{lb}", L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"], f"Thigh.{lb}")
    L.translate["Pelvis"] = "_bob"

    # ----- 躯干（直立建模 → 前倾）：细腰枪铁躯 + 小胸甲 + 背椎钉 -----
    L.xform = H
    L.tube("torso", "Chest", TORSO_P, TORSO_R, "armor", n=8, up=(0, 1, 0))
    L.cap("breastplate", "Chest", (0, 0.04, 1.30), (0, 1, 0.15), (0.19, 0.17, 0.12), "armor", theta=1.0, nu=8, nv=2,
          thick=0.012, fwd=(0, 0, 1))
    for k, z in enumerate((1.18, 1.27, 1.36)):
        cy, dep, _ = section(TORSO_P, TORSO_R, z)
        L.spike(f"spine stud {k}", "Chest", (0, cy - dep + 0.01, z), (0, cy - dep - 0.05, z + 0.03), 0.02, "trim", sides=3)
    L.xform = None
    for side, lb in SIDES:
        sh = L.J[f"shoulder.{lb}"]
        L.cable(f"tendon {lb}", "Chest", [H @ Vector((side * 0.05, -0.11, 1.22)), H @ Vector((side * 0.12, -0.11, 1.38)),
                                          sh + Vector((0, -0.05, 0.03))], 0.018, "armor", per=3, n=5)
        pc = sh + Vector((side * 0.015, -0.01, 0.03))
        pax = (side * 0.6, -0.1, 0.8)
        pr = (0.09, 0.09, 0.07) if not E else (0.12, 0.12, 0.10)
        L.cap(f"shoulder cap {lb}", "Chest", pc, pax, pr, "armor", theta=1.3, nu=7, nv=2, thick=0.01)
        if E:
            L.trim(f"shoulder rim {lb}", "Chest", cap_rim(pc, pax, pr, 1.3, 7, grow=0.004), 0.008, "trim", n=3, closed=True)
            top = pc + Vector(pax).normalized() * pr[2]
            L.spike(f"shoulder spike {lb}", "Chest", top, top + Vector((side * 0.10, -0.03, 0.16)), 0.028, "trim", sides=4)

    # ----- 头：尖兜帽 + 骨白面具 + 三点感光 + 下垂破帷 -----
    hood_c, hood_ax, hood_r, hood_th, hood_ph = hc + Vector((0, -0.02, 0.0)), (0, -0.25, 1), (0.13, 0.145, 0.15), 1.95, (0.85, TAU - 0.85)
    L.cap("hood", "Head", hood_c, hood_ax, hood_r, "cloth", theta=hood_th, nu=9, nv=4, phi=hood_ph,
          shape=lambda p, th, ph: p + Vector((0, -0.10 * (1 - th / 1.95) ** 2, 0.12 * (1 - th / 1.95) ** 3)))
    # 肩披：兜帽下的破边短披肩，俯视时让肩线更宽、更“披挂”
    mc, max_, mr, mth, mph = H @ Vector((0, -0.01, 1.40)), Vector((0, -0.25, 1)), (0.25, 0.19, 0.13), 1.45, (1.1, TAU - 1.1)
    L.cap("mantle", "Chest", mc, max_, mr, "cloth", theta=mth, nu=9, nv=3, phi=mph)
    for k, top in enumerate(cap_rim(mc, max_, mr, mth, 8, phi=mph)[1:8]):
        L.strip(f"mantle tatter {k}", "Chest", top, (top.x * 0.9, -0.15, -1), (1, 0, 0), 0.085, 0.16 + 0.07 * (k % 2),
                jag=((0.6, 1.0, 0.75) if k % 2 else (1.0, 0.7, 0.85)), nv=2)
    mask_c = hc + Vector((0, 0.045, -0.01))
    mask_ax = Vector((0, 0.97, -0.2)).normalized()
    L.cap("mask", "Head", mask_c, mask_ax, (0.075, 0.10, 0.05), "trim", theta=1.2, nu=8, nv=2, fwd=(0, 0, 1),
          thick=0.01, shape=lambda p, th, ph: Vector((p.x, p.y * (1.25 if p.y < 0 else 1.0), p.z)))
    face = mask_c + mask_ax * 0.05
    for k, (dx, dz) in enumerate(((-0.028, 0.03), (0.028, 0.03), (0.0, -0.008))):
        L.gem(f"sensor {k}", "Head", face + Vector((dx, 0.008 - abs(dx) * 0.3, dz)), 0.02 if not E else 0.022, "glow",
              stretch=(1, 0.7, 1), sides=4)
    for k, dx in enumerate((-0.045, 0.0, 0.045)):
        top = face + Vector((dx, 0.005 - abs(dx) * 0.4, -0.05))
        L.strip(f"veil {k}", "Head", top, (dx * 0.8, 0.12, -1), (1, 0, 0), 0.05, 0.24 + 0.06 * (k == 1),
                jag=((0.7, 1.0, 0.8) if k % 2 == 0 else (1.0, 0.8, 0.95)), nv=3)
    rim = cap_rim(hood_c, hood_ax, hood_r, hood_th, 9, phi=hood_ph)
    for k, i in enumerate((1, 3, 5, 7, 9)):
        top = rim[i]
        L.strip(f"hood tatter {k}", "Head", top, (top.x * 0.8, -0.3 - 0.2 * (i in (3, 5, 7)), -1), (1, 0, 0), 0.09,
                0.24 + 0.08 * (k % 2), jag=((0.6, 1.0, 0.7) if k % 2 else (1.0, 0.7, 0.85)), nv=3)

    # ----- 手臂：细臂 + 骨白长刃（精英：新月长镰） -----
    for side, lb in SIDES:
        sh, el, wr = L.J[f"shoulder.{lb}"], L.J[f"elbow.{lb}"], L.J[f"wrist.{lb}"]
        fa = f"Forearm.{lb}"
        L.tube(f"upper arm {lb}", f"UpperArm.{lb}", [sh, el], [0.045, 0.036], "armor", n=6)
        L.tube(f"forearm {lb}", fa, [el, wr], [0.038, 0.034], "armor", n=6)
        L.wrap(f"vambrace {lb}", fa, el.lerp(wr, 0.1), el.lerp(wr, 1.05), 0.05, 0.055, (side, 0.2, 0), "armor", arc=2.6,
               nu=4, nv=2, thick=0.01)
        d = (wr - el).normalized()
        d = (d + Vector((0, 0.05, 0))).normalized()
        w = blade_axes(side, d)
        o = wr + d * 0.01
        if not E:
            # 微弧长刃：刃背外拱、刃尖回收（类似太刀弧度），比直板更“快”
            spine, edge = [], []
            for k in range(7):
                t = k / 6
                c = 0.05 * math.sin(math.pi * t) - 0.03 * t * t
                wd = 0.062 * (1 - t) ** 0.6 + 0.004
                spine.append((0.80 * t - 0.02, c + wd * 0.35))
                edge.append((0.80 * t - 0.02, c - wd * 0.65))
            out = spine + list(reversed(edge))
            spine = [(x, y + 0.003) for x, y in spine[:-1]]
            edge = None
        else:
            # 新月长镰：刃体沿弧线外弯，尖端回勾
            spine, edge = [], []
            for k in range(8):
                t = k / 7
                c = 0.22 * math.sin(math.pi * t * 0.9) - 0.05 * t        # 刃体中线向外拱出
                wd = 0.08 * (1 - t) ** 0.7 + 0.006
                spine.append((0.98 * t, c + wd * 0.35))
                edge.append((0.98 * t, c - wd * 0.65))                  # 刃口在内凹一侧
            out = spine + list(reversed(edge))
            spine = [(x, y + 0.004) for x, y in spine]
            edge = [(x, y - 0.004) for x, y in edge]
        L.plate(f"blade {lb}", fa, out, 0.014, "trim", origin=o, xaxis=d, yaxis=w)
        L.trim(f"blade spine {lb}", fa, [o + d * x + w * y for x, y in spine], 0.008, "armor", n=3)
        if edge:
            L.trim(f"blade edge {lb}", fa, [o + d * x + w * y for x, y in edge[:-1]], 0.006, "glow", n=3)
        L.ring(f"blade collar {lb}", fa, o, d, 0.045, 0.012, "armor", count=6, n=3)

    # ----- 骨盆：髋管 + 腰带 + 前垂布 + 后燕尾（Tails 骨） -----
    L.tube("hips", "Pelvis", [(0, 0, 0.90), (0, 0, 0.98), (0, 0, 1.05)], [(0.085, 0.12), (0.095, 0.13), (0.085, 0.115)],
           "armor", n=8, up=(0, 1, 0))
    L.ring("belt", "Pelvis", (0, 0, 1.0), (0, 0, 1), 0.135, 0.016, "cloth", count=8, n=3, squash=0.72)
    L.strip("loin", "Pelvis", (0, 0.10, 0.99), (0, 0.25, -1), (1, 0, 0), 0.09, 0.30, jag=(0.8, 1.0, 0.7), cup=0.01)
    k_len = 1.25 if E else 1.0
    for k, (x, ln, w) in enumerate(((-0.07, 0.52, 0.09), (0.0, 0.62, 0.10), (0.07, 0.48, 0.09))):
        L.strip(f"tail {k}", "Tails", (x, -0.10, 1.01), (x * 0.6, -0.22, -1), (1, 0, 0), w, ln * k_len,
                jag=((0.7, 1.0, 0.8) if k != 1 else (0.9, 1.0, 0.65)), cup=-0.012, curl=-0.03, nv=4)

    # ----- 反关节长腿 -----
    for side, lb in SIDES:
        hp, kn, an = L.J[f"hip.{lb}"], L.J[f"knee.{lb}"], L.J[f"ankle.{lb}"]
        hock = Vector((side * 0.115, -0.11, 0.30))
        th, sh = f"Thigh.{lb}", f"Shin.{lb}"
        L.tube(f"thigh {lb}", th, [hp, kn], [0.07, 0.05], "armor", n=6)
        L.wrap(f"thigh plate {lb}", th, hp.lerp(kn, 0.05), hp.lerp(kn, 0.8), 0.08, 0.065, (side * 0.6, 0.8, 0), "armor",
               arc=2.3, nu=4, nv=2, thick=0.01)
        L.cap(f"knee {lb}", sh, kn + Vector((0, 0.025, 0.01)), (0, 1, 0.3), (0.058, 0.058, 0.045), "armor", theta=1.2,
              nu=6, nv=2, thick=0.01)
        L.spike(f"knee spike {lb}", sh, kn + Vector((0, 0.05, 0.02)), kn + Vector((0, 0.14, 0.08)), 0.02, "armor", sides=3)
        L.tube(f"shin {lb}", sh, [kn, hock], [0.046, 0.036], "armor", n=6)
        L.wrap(f"shin plate {lb}", sh, kn.lerp(hock, 0.1), kn.lerp(hock, 0.85), 0.056, 0.046, (0, 0.6, 0.8), "armor",
               arc=2.2, nu=4, nv=2, thick=0.008)
        L.spike(f"hock spur {lb}", sh, hock, hock + Vector((0, -0.10, 0.03)), 0.022, "armor", sides=3)
        L.tube(f"metatarsus {lb}", sh, [hock, an + Vector((0, -0.01, 0.0))], [0.034, 0.03], "armor", n=5)
        x = an.x
        for dx in (-0.025, 0.025):
            L.spike(f"toe {lb}{dx:+.3f}", sh, (x + dx * 0.5, an.y - 0.01, 0.04), (x + dx * 1.4, an.y + 0.14, 0.005), 0.018,
                    "armor", sides=3)
        L.spike(f"heel claw {lb}", sh, (x, an.y - 0.02, 0.04), (x, an.y - 0.10, 0.004), 0.014, "armor", sides=3)

    if E:
        L.halo_crown("halo crown", "Head", hc + Vector((0, -0.07, 0.12)), (0, -0.45, 0.9), 0.17, spikes=9, length=0.09,
                     r=0.009, tilt=0.35)
        L.gem("core", "Chest", H @ Vector((0, 0.17, 1.30)), 0.035, "glow", stretch=(0.8, 0.5, 1.3), sides=4)
    return L.finalize()


# ===== 动作 =====
REVIEW_POSE = ("Attack", 1)


def stand(rig, st):
    p = {}
    shift(p, st, z=-0.03)
    p["Tails"] = R((X, -0.05))
    for lb in ("L", "R"):
        plant(rig, st, p, lb, (0, 0, 0), ((-1 if lb == "L" else 1) * 0.1, 1, 0))
    return p


def move(rig, st, t):
    """低身疾奔：大步幅、前倾，双刃向后拖曳（刃尖扫在身后），燕尾向后扬起。"""
    p = {}
    shift(p, st, z=-0.05 - 0.035 * math.cos(2 * (t - 1.2)))
    p["Pelvis"] = R((Z, -0.12 * math.cos(t)), (X, 0.05))
    p["Chest"] = R((X, -0.20), (Z, 0.16 * math.cos(t)), (Y, -0.04 * math.sin(t)))
    p["Head"] = R((X, 0.18), (Z, -0.08 * math.cos(t)))
    for lb, sg in (("L", -1), ("R", 1)):
        p[f"UpperArm.{lb}"] = R((X, -0.95 + 0.16 * sg * math.cos(t)), (Y, sg * 0.18))
        p[f"Forearm.{lb}"] = R((X, -0.35))
    steps(rig, st, p, t, stride=0.62, lift=0.18, stance=0.38, pole_out=0.1)
    p["Tails"] = R((X, -0.75 - 0.10 * math.sin(2 * t)), (Y, 0.06 * math.sin(t)))
    return p


def slash_key(rig, st, stage):
    """交叉斩：1 伏身双刃外张上扬 / 2 突进交叉斩下 / 3 收势。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=-0.12)
        p["Chest"] = R((X, -0.22))
        p["Head"] = R((X, 0.2))
        for lb, sg in (("L", -1), ("R", 1)):
            rig.aim(p, f"UpperArm.{lb}", (sg * 0.55, -0.15, 0.82))
            rig.aim(p, f"Forearm.{lb}", (sg * 0.30, -0.35, 0.89))
        plant(rig, st, p, "L", (0, 0.12, 0), (-0.1, 1, 0))
        plant(rig, st, p, "R", (0, -0.10, 0), (0.1, 1, 0))
        p["Tails"] = R((X, -0.20))
    else:
        f = stage == 3
        shift(p, st, z=-0.14, y=0.26)
        p["Chest"] = R((X, -0.42 if not f else -0.48))
        p["Head"] = R((X, 0.35))
        for lb, sg in (("L", -1), ("R", 1)):
            rig.aim(p, f"UpperArm.{lb}", (-sg * 0.15, 0.90, -0.40))
            rig.aim(p, f"Forearm.{lb}", (-sg * (0.62 if not f else 0.75), 0.68 if not f else 0.45, -0.40 if not f else -0.5))
        plant(rig, st, p, "L", (0, 0.40, 0), (-0.1, 1, 0))
        plant(rig, st, p, "R", (0, -0.20, 0.04), (0.1, 1, 0))
        p["Tails"] = R((X, -0.60))
    return p


def slam_key(rig, st, stage):
    """精英双镰砸地：1 跃起双镰过顶后扬 / 2 砸入身前地面 / 3 压住。"""
    if stage == 0:
        return stand(rig, st)
    p = {}
    if stage == 1:
        shift(p, st, z=0.10)
        p["Chest"] = R((X, 0.16))
        p["Head"] = R((X, -0.05))
        for lb, sg in (("L", -1), ("R", 1)):
            rig.aim(p, f"UpperArm.{lb}", (sg * 0.30, 0.05, 0.95))
            rig.aim(p, f"Forearm.{lb}", (sg * 0.10, -0.35, 0.93))
        plant(rig, st, p, "L", (0, 0.04, 0.08), (-0.1, 1, 0))
        plant(rig, st, p, "R", (0, -0.04, 0.08), (0.1, 1, 0))
        p["Tails"] = R((X, 0.15))
    else:
        f = stage == 3
        shift(p, st, z=-0.20, y=0.08)
        p["Chest"] = R((X, -0.55 if not f else -0.50))
        p["Head"] = R((X, 0.40))
        for lb, sg in (("L", -1), ("R", 1)):
            rig.aim(p, f"UpperArm.{lb}", (sg * 0.30, 0.80, -0.52))
            rig.aim(p, f"Forearm.{lb}", (sg * 0.18, 0.55, -0.82))
        plant(rig, st, p, "L", (-0.03, 0.14, 0), (-0.2, 1, 0))
        plant(rig, st, p, "R", (0.03, -0.12, 0), (0.2, 1, 0))
        p["Tails"] = R((X, -0.45 if not f else -0.3))
    return p


def animate(rig, st):
    rig.loop("Move", 16, lambda t: move(rig, st, t), step=1)
    if st["elite"]:
        k = [slam_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (7, k[1]), (10, k[2]), (15, k[3]), (22, k[0])])
    else:
        k = [slash_key(rig, st, i) for i in range(4)]
        rig.keyed("Attack", [(1, k[0]), (5, k[1]), (8, k[2]), (11, k[3]), (17, k[0])])
