"""奥瑞利安 · 以太守卫（Aurelian, The Aether Warden）。

设定：白银板甲 + 黄铜雕饰 + 青绿以太光。T 形光缝大头盔两侧展开羽翼冠；背后悬浮可旋转的“圣盾矩阵”
环盾（技能：圣盾破阵）；白底青纹前后垂饰、午夜青披风。动作：Idle / Move（奔跑）/ Cast（横扫破阵）/
Channel（天坠之枪：环盾升至头顶、右臂指天）。
"""

import math

from mathutils import Matrix, Vector

from kit.core import (TAU, circuit_maps, ellipsoid, filigree_maps, finish, gem, interp, invdist, join, lerp,
                      orient, plate, projector, radial, rigid, ring_points, smoothstep, spike, surface, trim,
                      tube)
from kit.garment import Panel, Wrap
from kit.humanoid import (SIDES, Body, add_skeleton, cuisse, gorget, greave, hand, limb_plate, pauldron,
                          poleyn, rerebrace, sabaton, shell, suit_arm, suit_leg, suit_torso, torso_inlay, vambrace)
from kit.motion import blend, fingers, gait, idle, Legs
from kit.rig import R, X, Y, Z

TITLE = "Aurelian"
ACCENT = (0.49, 0.93, 0.88)
CLIPS = ("Idle", "Move", "Cast", "Channel")
GAME_TRIS = 62000
TEAL = ACCENT


def materials(ctx):
    M = ctx.M
    ctx.mat("silver", "white silver plate", (0.86, 0.88, 0.92), metal=1.0, rough=0.28, coat=0.35)
    ctx.texture("silver", filigree_maps((0.80, 0.82, 0.86), (0.52, 0.54, 0.58), size=1024, seed=4, density=22,
                                        width=1), normal_strength=0.35)
    ctx.mat("brass", "engraved brass", (0.83, 0.60, 0.27), metal=1.0, rough=0.28)
    ctx.mat("suit", "navy undersuit", (0.016, 0.022, 0.032), metal=0.1, rough=0.6, sheen=0.1,
            sheen_tint=(0.4, 0.6, 0.7))
    ctx.mat("tabard", "ivory aether tabard", (0.70, 0.68, 0.62), rough=0.7, sheen=0.1, sheen_tint=(0.8, 1, 1),
            spec=0.3)
    ctx.texture("tabard", circuit_maps(TEAL, base_rgb=(0.62, 0.60, 0.55), line_rgb=(0.05, 0.22, 0.22),
                                       size=1024, seed=21, buses=9), emit_strength=2.6)
    ctx.mat("cape", "midnight teal velvet", (0.012, 0.032, 0.040), rough=0.8, sheen=0.08,
            sheen_tint=(0.3, 0.6, 0.6), spec=0.28)
    ctx.texture("cape", circuit_maps(TEAL, base_rgb=(0.010, 0.026, 0.032), size=2048, seed=33, buses=13),
                emit_strength=2.4)
    ctx.mat("lining", "deep teal satin lining", (0.020, 0.075, 0.085), rough=0.45, sheen=0.35,
            sheen_tint=(0.5, 1, 1))
    ctx.mat("visor", "black glass visor", (0.006, 0.008, 0.010), metal=0.1, rough=0.07, coat=1.0, spec=0.8)
    ctx.mat("glow", "aether core glow", (0.4, 0.8, 0.78), emit=TEAL, strength=8.0)
    ctx.mat("inlay", "aether circuit inlay", (0.25, 0.5, 0.48), emit=TEAL, strength=3.2)
    ctx.mat("hem", "aether hem light", (0.2, 0.45, 0.42), emit=TEAL, strength=4.5)
    ctx.mat("blade", "aether blade crystal", (0.05, 0.10, 0.11), metal=0.8, rough=0.15, coat=1.0)
    return M


# ===== 头盔 =====
def build_helm(ctx, B, M):
    s = B.s
    hc = Vector((0, 0.014 * s, B.z(1.885)))
    rx, ry = 0.108 * s, 0.124 * s
    # 糖锥形大盔：顶部收尖、眉线最宽、下颌外扩护住喉部
    prof = [(0.0, (0.00, 0.170)), (0.12, (0.40, 0.152)), (0.30, (0.78, 0.102)), (0.50, (0.97, 0.036)),
            (0.60, (1.00, 0.006)), (0.74, (0.97, -0.045)), (0.87, (0.93, -0.095)), (1.0, (1.00, -0.142))]
    eye_z, slit_w = hc.z + 0.004 * s, 0.062 * s

    def hp(u, v):
        a = u * TAU
        r, dz = interp(prof, v)
        front = max(0.0, math.cos(a))
        x = rx * r * math.sin(a)
        y = ry * r * math.cos(a)
        z = hc.z + dz * s
        prow = 0.028 * s * math.exp(-(x / (0.020 * s)) ** 2) * front ** 2 * smoothstep(0.15, 0.9, v)
        fin = 0.0
        groove = 0.010 * s * math.exp(-((z - eye_z - 0.017 * s) / (0.006 * s)) ** 2) * front ** 1.5   # 眉檐
        if front > 0.3:
            groove -= 0.010 * s * math.exp(-((z - eye_z) / (0.0075 * s)) ** 2) * (1 - smoothstep(slit_w * 0.9, slit_w * 1.1, abs(x)))
            groove -= 0.008 * s * math.exp(-(x / (0.0065 * s)) ** 2) * smoothstep(eye_z - 0.078 * s, eye_z - 0.070 * s, z) * (1 - smoothstep(eye_z - 0.004 * s, eye_z + 0.002 * s, z))
        flare = 0.012 * s * smoothstep(0.86, 1.0, v)
        d = Vector((x, y, 0)).normalized() if r > 1e-4 else Vector((0, 0, 0))
        return Vector((x, y + hc.y + prow + groove * front, z)) + d * (fin + flare)
    helm = surface(f"{ctx.title} helm", hp, 64, 40, [M["silver"]])
    orient(helm, lambda c: hc)
    helm = finish(helm, 0.006 * s, -1, 1)
    ctx.part(helm, rigid("Head"))
    proj = projector(helm, (0, -1, 0))
    # T 形光缝：眉下横缝 + 鼻梁竖缝
    slit = [proj(Vector((x, 1, eye_z + 0.006 * s * (abs(x) / slit_w) ** 2)), 0.0010 * s)
            for x in [i / 18 * 2 * slit_w - slit_w for i in range(19)]]
    ctx.part(tube(f"{ctx.title} visor slit", slit, [0.0030 * s] * 19, [M["glow"]], n=8, fx=0.55, up=(0, 0, 1)),
             rigid("Head"))
    vert = [proj(Vector((0, 1, eye_z - 0.006 * s - i * 0.0068 * s)), 0.0010 * s) for i in range(10)]
    ctx.part(tube(f"{ctx.title} breath slit", vert, [0.0024 * s] * 10, [M["glow"]], n=8, fy=0.55), rigid("Head"))
    # 眉带 + 额心宝石 + 顶脊黄铜
    band = [radial(hp(i / 96, 0.50), 0.004 * s, hc.y) for i in range(96)]
    ctx.part(trim(f"{ctx.title} brow band", band, 0.0045 * s, M["brass"], closed=True), rigid("Head"))
    ctx.part(gem(f"{ctx.title} brow gem", proj(Vector((0, 1, hc.z + 0.045 * s)), 0.006 * s), 0.009 * s, M["glow"],
                 (0.8, 0.5, 1.5)), rigid("Head"))
    # 顶冠鳍：沿头盔中线从眉心越过盔顶到后颈，向后上方隆起
    path = [hp(0.0, v) for v in [0.50 - i / 30 * 0.50 for i in range(31)]]
    path += [hp(0.5, v) for v in [i / 30 * 0.74 for i in range(31)]][1:]

    def crest_at(t):
        f = t * (len(path) - 1)
        i = min(len(path) - 2, int(f))
        return path[i].lerp(path[i + 1], f - i)

    def crest_pt(u, v):
        p = crest_at(u)
        n = (p - hc).normalized()
        h = 0.060 * s * math.sin(math.pi * u) ** 0.7 * lerp(0.55, 1.25, u)
        return p + n * (h * v - 0.004 * s)
    fin_obj = surface(f"{ctx.title} crest", crest_pt, 60, 6, [M["silver"]])
    ctx.part(finish(fin_obj, 0.007 * s, 0, 1), rigid("Head"))
    ctx.part(trim(f"{ctx.title} crest edge", [crest_pt(i / 60, 1.0) for i in range(61)], 0.0030 * s, M["brass"]),
             rigid("Head"))
    for sd in (-1, 1):
        line = [crest_pt(i / 40, 0.55) + Vector((sd * 0.0040 * s, 0, 0)) for i in range(4, 37)]
        ctx.part(trim(f"{ctx.title} crest inlay {sd}", line, 0.0015 * s, M["inlay"]), rigid("Head"))
    bottom = [radial(hp(i / 96, 1.0), 0.004 * s, hc.y) for i in range(96)]
    ctx.part(trim(f"{ctx.title} helm rim", bottom, 0.0038 * s, M["brass"], closed=True), rigid("Head"))
    # 羽翼冠：两侧各六片刃羽向后上方展开
    lengths = (0.17, 0.22, 0.25, 0.25, 0.22, 0.18, 0.13)
    for side, label in SIDES:
        base = Vector((side * (rx + 0.006 * s), hc.y - 0.028 * s, hc.z + 0.036 * s))
        for i, L in enumerate(lengths):
            phi = math.radians(8 + i * 11.5)
            d = Vector((side * 0.28, -math.cos(phi), math.sin(phi))).normalized()
            n = Vector((side, 0, 0))
            ya = d.cross(n).normalized()
            L *= s

            def lower(t):
                return -(0.020 + 0.018 * math.sin(math.pi * t) ** 0.8) * s * (1 - 0.6 * t)
            outline = [(0, -0.008 * s)] + [(k / 10 * L, lower(k / 10)) for k in range(1, 11)] + [(L * 1.05, 0.0)]
            outline += [(k / 10 * L, (0.008 + 0.008 * math.sin(math.pi * k / 10)) * s * (1 - 0.5 * k / 10))
                        for k in range(10, 0, -1)] + [(0, 0.008 * s)]
            mat = M["brass"] if i % 2 else M["silver"]
            origin = base + d * 0.006 * s * i
            fe = plate(f"{ctx.title} wing {label}{i}", outline, 0.006 * s, [mat], origin=origin, xaxis=d, yaxis=ya,
                       bulge=lambda x, y, L=L: 0.014 * s * math.sin(math.pi * x / L), bev=0.0014 * s)
            ctx.part(fe, rigid("Head"))
            pn = d.cross(ya).normalized()
            edge = [origin + d * (k / 14 * L) + ya * (lower(k / 14) - 0.0016 * s)
                    + pn * 0.014 * s * math.sin(math.pi * k / 14) for k in range(1, 15)]
            ctx.part(trim(f"{ctx.title} wing edge {label}{i}", edge, 0.0016 * s, M["inlay"] if i in (0, 3) else M["brass"]),
                     rigid("Head"))
        rosette = base + Vector((side * 0.006 * s, 0, 0))
        ctx.part(ellipsoid(f"{ctx.title} wing boss {label}", rosette, (0.012 * s, 0.020 * s, 0.020 * s), [M["brass"]], 16, 10),
                 rigid("Head"))
        ctx.part(gem(f"{ctx.title} wing gem {label}", rosette + Vector((side * 0.010 * s, 0, 0)), 0.007 * s, M["glow"],
                     (0.6, 1, 1)), rigid("Head"))
    return hc


# ===== 圣盾矩阵（背后环盾，挂 Aegis 骨，网页端绕法线旋转） =====
AEGIS_C = (0.0, -0.30, 1.73)


def build_aegis(ctx, B, M):
    s = B.s
    c = Vector(AEGIS_C) * s
    objs = []
    xa, za = Vector((1, 0, 0)), Vector((0, 0, 1))

    def at(theta, r):
        return c + xa * math.sin(theta) * r * s + za * math.cos(theta) * r * s
    objs.append(tube(f"{ctx.title} aegis rim", [at(i / 96 * TAU, 0.405) for i in range(96)], [0.012 * s] * 96,
                     [M["brass"]], n=8, fx=1.0, fy=0.45, up=(0, 1, 0), closed=True, per=1))
    for k in range(16):
        t0, t1 = (k + 0.08) / 16 * TAU, (k + 0.92) / 16 * TAU
        outline = []
        for i in range(7):
            th = lerp(t0, t1, i / 6)
            outline.append((math.sin(th) * 0.385 * s, math.cos(th) * 0.385 * s))
        for i in range(6, -1, -1):
            th = lerp(t0 + 0.03, t1 - 0.03, i / 6)
            outline.append((math.sin(th) * 0.285 * s, math.cos(th) * 0.285 * s))
        seg = plate(f"{ctx.title} aegis plate {k}", outline, 0.010 * s, [M["silver"]], origin=c, xaxis=xa, yaxis=za,
                    bulge=lambda x, y: -0.03 * s * (1 - (x * x + y * y) / (0.40 * s) ** 2), bev=0.0015 * s)
        objs.append(seg)
    for r, mat, rad in ((0.268, M["glow"], 0.0045), (0.245, M["brass"], 0.0055), (0.105, M["brass"], 0.005)):
        objs.append(tube(f"{ctx.title} aegis ring {r}", [at(i / 72 * TAU, r) + Vector((0, -0.012 * s, 0)) for i in range(72)],
                         [rad * s] * 72, [mat], n=6, closed=True, per=1))
    for k in range(12):
        th = k / 12 * TAU
        objs.append(tube(f"{ctx.title} aegis spoke {k}", [at(th, 0.11) + Vector((0, -0.014 * s, 0)), at(th, 0.24) + Vector((0, -0.020 * s, 0))],
                         [0.0035 * s, 0.0035 * s], [M["glow"] if k % 3 == 0 else M["brass"]], n=6, per=1))
    star = []
    for i in range(16):
        th = i / 16 * TAU
        r = 0.095 if i % 2 == 0 else (0.040 if i % 4 else 0.055)
        star.append((math.sin(th) * r * s, math.cos(th) * r * s))
    objs.append(plate(f"{ctx.title} aegis star", star, 0.012 * s, [M["brass"]], origin=c + Vector((0, -0.02 * s, 0)),
                      xaxis=xa, yaxis=za, bev=0.002 * s))
    objs.append(ellipsoid(f"{ctx.title} aegis heart", c + Vector((0, -0.032 * s, 0)), (0.030 * s, 0.014 * s, 0.030 * s),
                          [M["glow"]], 20, 12))
    for k in range(12):
        th = k / 12 * TAU
        L = 0.17 if k == 0 else (0.11 if k in (3, 9) else 0.065)
        objs.append(spike(f"{ctx.title} aegis ray {k}", at(th, 0.405), at(th, 0.405 + L), 0.016 * s,
                          [M["silver"] if k % 2 else M["brass"]], sides=4, fx=1.0, fy=0.35, up=(0, 1, 0)))
        if k % 3 == 0:
            objs.append(gem(f"{ctx.title} aegis node {k}", at(th, 0.335) + Vector((0, -0.012 * s, 0)), 0.010 * s,
                            M["glow"], (1, 0.6, 1)))
    aegis = join(objs, f"{ctx.ID}_AEGIS", c)
    aegis.rotation_euler = (math.radians(-10), 0, 0)
    ctx.attach(aegis, "Aegis", keep=True)
    return c


def build_blade(ctx, B, M):
    """展示页环绕用的以太剑（游戏内由原生飞剑绘制，不进 LOD）。"""
    s = B.s
    prof = [(-0.10, 0.0), (-0.07, 0.8), (-0.05, 1.0), (0.0, 0.85), (0.30, 0.55), (0.46, 0.0)]
    ys = [y * s for y, _ in prof]
    ws = [w * 0.024 * s for _, w in prof]
    core = tube(f"{ctx.title} blade core", [(0, y, 0) for y in ys], ws, [M["blade"]], n=4, fx=0.30, up=(0, 0, 1), per=4)
    fuller = tube(f"{ctx.title} blade fuller", [(0, y, 0) for y in ys[2:-1]], [0.0026 * s] * (len(ys) - 3),
                  [M["hem"]], n=6, per=4)
    guard = tube(f"{ctx.title} blade guard", [(-0.05 * s, -0.055 * s, 0), (0, -0.045 * s, 0), (0.05 * s, -0.055 * s, 0)],
                 [0.004 * s, 0.009 * s, 0.004 * s], [M["brass"]], n=6)
    blade = join([core, fuller, guard], f"{ctx.ID}_BLADE", Vector((0.8, 0.05, 1.5)) * s)
    ctx.hidden.append(blade)


# ===== 布料 =====
def cloth(B):
    s = B.s
    cape = Wrap("Cape", "Chest", math.pi - 1.48, math.pi + 1.48, top=lambda u: B.z(1.675) - 0.02 * s * abs(math.sin((u - 0.5) * math.pi)),
                bottom=B.z(0.20), r_top=(0.245 * s, 0.140 * s), r_bot=(0.60 * s, 0.50 * s), K=5, cy=-0.02 * s,
                joints=(0, 0.16, 0.34, 0.52, 0.74, 1.0),
                flow=0.16 * s, folds=(5.0, 0.006 * s, 0.045 * s), seed=2.4, tails=7, tail_len=(0.06 * s, 0.03 * s),
                curl=(0.03 * s, 0.01 * s), flare_exp=1.1)
    front = Panel("TabardF", "Pelvis", B.z(1.245), B.z(0.26), [(0, 0.27 * s), (0.5, 0.24 * s), (1.0, 0.18 * s)],
                  [(0, 0.128 * s), (0.1, 0.150 * s), (0.4, 0.165 * s), (1.0, 0.150 * s)], side=1, point=0.10)
    back = Panel("TabardB", "Pelvis", B.z(1.245), B.z(0.34), [(0, 0.28 * s), (0.5, 0.25 * s), (1.0, 0.20 * s)],
                 [(0, 0.122 * s), (0.1, 0.140 * s), (0.4, 0.160 * s), (1.0, 0.160 * s)], side=-1, point=0.10)
    return cape, front, back


def build(ctx):
    M = materials(ctx)
    B = Body(height=2.0, shoulder=0.215, bulk=1.05, chest=1.04, limb=1.02)
    s = B.s
    suit_torso(ctx, B, M["suit"])
    for side, label in SIDES:
        suit_arm(ctx, B, side, label, M["suit"])
        suit_leg(ctx, B, side, label, M["suit"])
        hand(ctx, B, side, label, M["silver"], glow=M["glow"], scale=1.14)
    # 胸甲：胸肌两块起伏、前缘 V 口、黄铜滚边
    pec = lambda a, z: 0.013 * s * math.exp(-((z - B.z(1.51)) / (0.065 * s)) ** 2) * max(0.0, math.cos(a)) ** 2 * (1 - 0.6 * math.exp(-(math.sin(a) / 0.10) ** 2))
    shell(ctx, B, f"{ctx.title} cuirass", lambda a: B.z(1.665) - 0.06 * s * max(0.0, math.cos(a)) ** 8,
          lambda a: B.z(1.33) - 0.05 * s * max(0.0, math.cos(a)) ** 6, 0.012 * s, M["silver"],
          invdist(["Spine", "Chest"]), thick=0.008 * s, trims=(M["brass"], 0.0034 * s), shape=pec)
    # 前腹甲（胸甲下缘的尖形护腹板）
    shell(ctx, B, f"{ctx.title} plackart", lambda a: B.z(1.43), lambda a: B.z(1.25) - 0.07 * s * max(0.0, math.cos(a)) ** 3,
          0.024 * s, M["silver"], invdist(["Pelvis", "Spine"]), a0=-1.05, a1=1.05, nu=40, nv=14, thick=0.006 * s,
          trims=(M["brass"], 0.0028 * s))
    # 腰带与三层腹甲裙
    shell(ctx, B, f"{ctx.title} belt", B.z(1.285), B.z(1.245), 0.030 * s, M["brass"], invdist(["Pelvis", "Spine"]),
          nu=72, nv=4, thick=0.006 * s)
    for k, (zt, zb, g) in enumerate(((1.25, 1.17, 0.034), (1.19, 1.11, 0.040), (1.13, 1.05, 0.046))):
        shell(ctx, B, f"{ctx.title} fauld {k}", B.z(zt), lambda a, zb=zb: B.z(zb) - 0.03 * s * max(0.0, math.cos(a)) ** 4,
              g * s, M["silver"], rigid("Pelvis"), a0=0.55, a1=TAU - 0.55, nu=56, nv=6, thick=0.006 * s,
              trims=(M["brass"], 0.0026 * s))
    buckle = B.on_torso(0, B.z(1.265), 0.040 * s)
    ctx.part(ellipsoid(f"{ctx.title} buckle", buckle, (0.032 * s, 0.012 * s, 0.024 * s), [M["brass"]], 20, 12), rigid("Pelvis"))
    ctx.part(gem(f"{ctx.title} buckle gem", buckle + Vector((0, 0.011 * s, 0)), 0.010 * s, M["glow"], (1.2, 0.5, 0.9)),
             rigid("Pelvis"))
    # 胸核：菱形以太宝石 + 黄铜星框 + 八道放射嵌线
    core = B.on_torso(0, B.z(1.515), 0.030 * s)
    ctx.part(gem(f"{ctx.title} chest core", core + Vector((0, 0.004 * s, 0)), 0.020 * s, M["glow"], (0.75, 0.45, 1.35)),
             rigid("Chest"))
    frame = [core + Vector((math.sin(t) * 0.030 * s * (1 + 0.5 * (i % 2)), 0.002 * s, math.cos(t) * 0.042 * s * (1 + 0.4 * (i % 2))))
             for i, t in enumerate([k / 8 * TAU for k in range(8)])]
    ctx.part(trim(f"{ctx.title} core frame", frame, 0.0040 * s, M["brass"], closed=True), rigid("Chest"))
    torso_inlay(ctx, B, [[(0.030, 1.555), (0.060, 1.585), (0.105, 1.585), (0.130, 1.61)],
                         [(0.032, 1.495), (0.070, 1.470), (0.110, 1.470)],
                         [(0.018, 1.465), (0.018, 1.405), (0.045, 1.380), (0.045, 1.300)]],
                0.034 * s, M["inlay"], invdist(["Spine", "Chest"]), via_mat=M["glow"])
    torso_inlay(ctx, B, [[(0.0, 1.60), (0.0, 1.36)], [(0.02, 1.56), (0.09, 1.50), (0.09, 1.40)]], 0.024 * s,
                M["inlay"], invdist(["Spine", "Chest"]), back=True, via_mat=M["glow"])
    gorget(ctx, B, M["silver"], M["brass"])
    for side, label in SIDES:
        pauldron(ctx, B, side, label, M["silver"], M["brass"], M["glow"], lames=4, radius=0.142, spire=0.08,
                 spire_at=-0.25, theta=((0.05, 0.86), (0.60, 1.18), (1.00, 1.46), (1.34, 1.74)),
                 shrink=(1.0, 0.96, 0.92, 0.88), ridge=0.05)
        rerebrace(ctx, B, side, label, M["silver"], M["brass"])
        vambrace(ctx, B, side, label, M["silver"], M["brass"], inlay=M["inlay"], spur=(M["brass"], 0.05))
        a = B.arms[label]
        ctx.part(ellipsoid(f"{ctx.title} couter {label}", a["elbow"] + (a["elbow"] - B.arms[label]["shoulder"]).normalized() * 0.0 +
                           Vector((side * 0.018 * s, -0.030 * s, 0)), (0.030 * s, 0.028 * s, 0.034 * s), [M["silver"]], 18, 12),
                 rigid(("UpperArm." + label, 0.5), ("Forearm." + label, 0.5)))
        cuisse(ctx, B, side, label, M["silver"], M["brass"], r=(0.114, 0.095))
        poleyn(ctx, B, side, label, M["silver"], M["brass"], M["glow"], size=0.068)
        greave(ctx, B, side, label, M["silver"], M["brass"], r=(0.080, 0.062))
        sabaton(ctx, B, side, label, M["silver"], M["brass"], toe_mat=M["brass"])
        # 腿侧挂甲（随大腿摆动）
        L = B.legs[label]
        for k in range(2):
            limb_plate(ctx, f"{ctx.title} tasset {label}{k}", L["hip"] + Vector((0, 0, (0.10 - k * 0.07) * s)),
                       L["hip"].lerp(L["knee"], 0.42 - k * 0.12), (0.118 + k * 0.008) * s, (0.112 + k * 0.008) * s,
                       M["silver"], rigid(f"Thigh.{label}"), Vector((side, 0.25, 0)), arc=0.95, thick=0.006 * s,
                       trim_mat=M["brass"], rims=(1,))
    hc = build_helm(ctx, B, M)
    build_aegis(ctx, B, M)
    build_blade(ctx, B, M)
    cape, front, back = cloth(B)
    cape.build(ctx, [M["cape"], M["lining"]], f"{ctx.title} cape", nu=98, nv=64, uv_scale=1.2,
               hem=(M["hem"], 0.0028 * s), edges=(M["brass"], 0.0034 * s))
    front.build(ctx, [M["tabard"], M["lining"]], f"{ctx.title} tabard front", edges=(M["brass"], 0.0032 * s),
                spine=(M["inlay"], 0.0019 * s))
    back.build(ctx, [M["tabard"], M["lining"]], f"{ctx.title} tabard back", edges=(M["brass"], 0.0032 * s),
               spine=(M["inlay"], 0.0019 * s))
    return {"B": B, "cape": cape, "front": front, "back": back, "hc": hc}


def skeleton(rig, st):
    B = st["B"]
    add_skeleton(rig, B)
    c = Vector(AEGIS_C) * B.s
    rig.bone("Aegis", c, c + Vector((0, -0.12 * B.s, 0)), "Chest", roll=Z)
    rig.translate["Aegis"] = "_aegis"
    for g in (st["cape"], st["front"], st["back"]):
        rig.add_garment(g)


# ===== 动作 =====
REVIEW_POSE = ("Idle", 1)


def cloth_idle(rig, st, t, pose, amp=1.0):
    rig.wind(pose, st["cape"], lambda k, j: (0.03 + 0.025 * math.sin(t + k * 0.8 + j * 0.9)) * amp,
             lambda k, j: 0.02 * amp, lambda k, j: 0.015 * math.sin(t + k * 0.9 + j * 0.6) * amp)
    for g in (st["front"], st["back"]):
        rig.garment_pose(pose, g, lambda k, j: (0.02 + 0.02 * math.sin(t + j * 0.8)) * amp)


def tabard_clear(rig, st, pose, extra=0.0):
    """前垂饰按膝盖前移量外掀，保证跑动 / 弓步时膝盖不穿出布面。"""
    B, front = st["B"], st["front"]
    need = 0.05
    for label in ("L", "R"):
        knee = rig.tail(pose, f"Thigh.{label}")
        depth = front.depth(0.5) + 0.02 * B.s
        dz = max(0.2 * B.s, front._top - knee.z)
        need = max(need, math.atan2(knee.y + 0.075 * B.s - depth, dz))
    rig.garment_pose(pose, front, lambda k, j: need + extra)


def idle_pose(rig, st, t):
    p = idle(rig, st["B"], t, breathe=0.022, sway=0.012)
    p["_aegis"] = Vector((0, 0, 0.012 * math.sin(t)))
    p["Aegis"] = R((X, 0.025 * math.sin(t + 0.7)))
    cloth_idle(rig, st, t, p)
    return p


def move_pose(rig, st, t):
    B = st["B"]
    p = gait(rig, B, t, stride=0.50, lift=0.17, stance=0.38, bob=0.034, lean=0.17, twist=0.10, arm=0.62,
             elbow=1.10, arm_in=0.46)
    for label in ("L", "R"):
        fingers(p, B, label, 0.55)
    p["_aegis"] = Vector((0, -0.02 * B.s, 0.010 * math.cos(2 * t)))
    p["Aegis"] = R((X, 0.10 + 0.03 * math.cos(2 * t)))
    rig.wind(p, st["cape"], lambda k, j: 0.30 + 0.07 * math.sin(2 * t + k * 0.7 + j * 1.1),
             lambda k, j: 0.03, lambda k, j: 0.04 * math.sin(t + k * 0.6 + j * 0.8))
    rig.wind(p, st["back"], lambda k, j: 0.26 + 0.07 * math.sin(2 * t + j))
    tabard_clear(rig, st, p, 0.04 * math.sin(2 * t + 0.5))
    return p


def stance(rig, B, pose, lf, rf, sink, yaw_l=0.0, yaw_r=0.0):
    """弓步 / 马步：lf、rf 为左右脚踝相对静止位置的偏移 (x, y)。"""
    legs = Legs(rig, B)
    pose["_hover"] = -sink * B.s
    for label, off, yaw in (("L", lf, yaw_l), ("R", rf, yaw_r)):
        a = legs.rest[label]["ankle"] + Vector((off[0] * B.s, off[1] * B.s, 0))
        legs.plant(pose, label, a, yaw=yaw, knee_out=0.2)


def cast_key(rig, st, stage):
    B = st["B"]
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    if stage == 1:                                   # 蓄势：身体右拧，右臂后引
        p["Pelvis"] = R((Z, -0.20), (X, -0.05))
        p["Spine"] = R((Z, -0.15))
        p["Chest"] = R((Z, -0.25), (X, 0.04))
        stance(rig, B, p, (-0.02, 0.16), (0.03, -0.14), 0.07, 0.1, -0.35)
        rig.aim(p, "UpperArm.R", (0.75, -0.55, 0.05))
        rig.aim(p, "Forearm.R", (0.45, -0.75, 0.15))
        rig.aim(p, "UpperArm.L", (-0.45, 0.70, -0.45))
        rig.aim(p, "Forearm.L", (-0.1, 0.85, 0.2))
        p["_aegis"] = Vector((0, -0.04 * B.s, 0.02 * B.s))
        p["Aegis"] = R((X, 0.12))
        fingers(p, B, "R", 0.9)
    else:                                            # 横扫：左脚弓步，右掌自右向左劈开扇形缺口
        follow = stage == 3
        p["Pelvis"] = R((Z, 0.22 if not follow else 0.30), (X, -0.12))
        p["Spine"] = R((Z, 0.18), (X, -0.06))
        p["Chest"] = R((Z, 0.26 if not follow else 0.34))
        stance(rig, B, p, (-0.03, 0.30), (0.05, -0.26), 0.11, 0.25, -0.45)
        d = (-0.55, 0.82, 0.10) if not follow else (-0.85, 0.50, 0.06)
        rig.aim(p, "UpperArm.R", d)
        rig.aim(p, "Forearm.R", (d[0] * 1.05, d[1], d[2] + 0.02))
        rig.aim(p, "Hand.R", (d[0] * 1.1, d[1], d[2]))
        rig.aim(p, "UpperArm.L", (-0.35, 0.55, 0.45))
        rig.aim(p, "Forearm.L", (0.15, 0.55, 0.80))
        fingers(p, B, "R", -0.08)
        fingers(p, B, "L", 0.5)
        p["_aegis"] = Vector((0, 0.02 * B.s, 0.04 * B.s))
        p["Aegis"] = R((X, -0.22))
        rig.wind(p, st["cape"], lambda k, j: 0.34, lambda k, j: 0.04, lambda k, j: -0.10)
        rig.wind(p, st["back"], lambda k, j: 0.30)
    tabard_clear(rig, st, p)
    return p


def channel_key(rig, st, stage):
    B = st["B"]
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    p["Chest"] = R((X, 0.10))
    p["Neck"] = R((X, 0.10))
    p["Head"] = R((X, 0.18))
    stance(rig, B, p, (-0.07, 0.04), (0.07, -0.04), 0.06, 0.25, -0.25)
    rig.aim(p, "UpperArm.R", (0.18, 0.12, 1.0))
    rig.aim(p, "Forearm.R", (0.05, 0.10, 1.0))
    rig.aim(p, "Hand.R", (0.0, 0.08, 1.0))
    rig.aim(p, "UpperArm.L", (-0.55, 0.72, -0.22))
    rig.aim(p, "Forearm.L", (-0.35, 0.92, -0.10))
    fingers(p, B, "R", -0.1)
    fingers(p, B, "L", -0.05, 0.6)
    p["_aegis"] = Vector((0, 0.30 * B.s, 0.58 * B.s))     # 环盾升到头顶化作天环
    p["Aegis"] = R((X, -1.35))
    rig.wind(p, st["cape"], lambda k, j: 0.16, lambda k, j: 0.08)
    for g in (st["front"], st["back"]):
        rig.garment_pose(p, g, lambda k, j: 0.10)
    return p


def animate(rig, st):
    rig.loop("Idle", 72, lambda t: idle_pose(rig, st, t))
    rig.loop("Move", 16, lambda t: move_pose(rig, st, t), step=1)
    k = [cast_key(rig, st, i) for i in range(4)]
    rig.keyed("Cast", [(1, k[0]), (8, k[1]), (14, k[2]), (20, k[3]), (32, k[0])])
    c = [channel_key(rig, st, i) for i in range(2)]
    rig.keyed("Channel", [(1, c[0]), (13, c[1]), (28, c[1]), (42, c[0])])
