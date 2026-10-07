"""Boss 4 · 机械神祇 · 远古战争引擎（Deus Machina · Ancient War Engine）。

设定：约 7 m 高、悬浮的多臂机械神像。象牙白瓷甲 + 烫金结构 + 金色光缝；静谧的闭目瓷面具、头后扇形金冠；
六条手臂——上对高举光束发射器、中对张掌结印的机械手（掌心透镜）、下对前指的小发射器；背后由脊柱支架托起
三层同心光环（内两层刻发光符文、外层带光芒刺），胸口太阳核心；下半身不是腿，而是垂挂的分节甲片、
导管线缆与中央龙骨坠。
动作：Idle（悬浮呼吸、光环慢转、手臂缓动）/ Move（悬浮前移、手臂后摆、甲片拖曳）/
Attack（六臂对准前方、发射器蓄能齐射交叉光束）/ Enrage（光环加速、分离外扩，六臂全开）。
光束为半透明能量光束（白金芯线 + 金色光晕 + 脉冲环，见 _b4fx_beam），炮口有充能光晕，均随原有 Beam / Muzzle 骨缩放。

光环为 12 重旋转对称：循环动作里每条环只转过整数个 30° 步进（首尾几何完全重合），一次性动作转过整圈。
"""

import math

from mathutils import Matrix, Vector

from kit.core import (TAU, catmull, chain, circuit_maps, ellipsoid, filigree_maps, finish, frame_from, gem, interp,
                      invdist, lathe, lerp, orient, plate, projector, rigid, smoothstep, spike, surface, tube)
from kit.humanoid import SIDES
from kit.rig import I3, R, X, Y, Z, depth_w

from chars import _b4fx_beam as FX
from chars._b4_util import (ChainSet, axis_frame, band, circle, clearance, cyl_band, densify, ease, ellip, gauss,
                            grid, hinge, lathe_y, lin, loop, mirror, place, post, raise_axis, ring_around, ring_at,
                            rune_strip_maps, sampled, seam_check, slerp_m, spin_curve, stats, sunburst_maps, sweep,
                            track, with_defaults)

TITLE = "Deus Machina"
ACCENT = (1.0, 0.84, 0.53)
CLIPS = ("Idle", "Move", "Attack", "Enrage")
# 游戏版预算：原 85000 + 光束特效比旧实心光束多出的面数（1944，光束与光晕材质含 glow、不参与减面）。
# 这样本体的减面比例与特效轮之前完全一致，游戏版总面数约 8.69 万（<= 9 万）。
GAME_TRIS = 86944
LOD_KEEP = ("inlay", "glow", "hem", "trim", "core", "halo")
REVIEW_POSE = ("Idle", 1)


RUNE_GLOW = (1.0, 0.70, 0.28)      # 符文发光取更饱和的金色，经 AgX 压缩后仍读作金光而非白光


def trim(name, points, radius, mat, closed=False):
    """滚边 / 光缝细管：按粗细取 4 / 5 / 6 棱截面省面——这些材质在游戏版不参与减面。"""
    n = 4 if radius <= 0.012 else (5 if radius <= 0.02 else 6)
    return tube(name, points, [radius] * len(points), [mat], n=n, closed=closed, per=1)


# ===== 材质 =====
def materials(ctx):
    M = ctx.M
    ctx.mat("ivory", "ivory war plate", (0.86, 0.79, 0.64), metal=0.10, rough=0.32, coat=0.55)
    ctx.texture("ivory", filigree_maps((0.86, 0.79, 0.64), (0.78, 0.68, 0.50), size=1024, seed=41, density=18,
                                       width=1), normal_strength=0.22)
    ctx.mat("gold", "burnished gold", (0.98, 0.80, 0.50), metal=1.0, rough=0.26)
    ctx.texture("gold", filigree_maps((0.98, 0.80, 0.50), (0.62, 0.44, 0.20), size=1024, seed=42, density=16,
                                      width=1), normal_strength=0.40)
    ctx.mat("trim", "gold trim", (1.0, 0.84, 0.56), metal=1.0, rough=0.22)
    ctx.mat("dark", "dark bronze mechanism", (0.05, 0.042, 0.036), metal=0.9, rough=0.36)
    ctx.texture("dark", circuit_maps(RUNE_GLOW, base_rgb=(0.045, 0.038, 0.032), line_rgb=(0.20, 0.14, 0.06),
                                     size=1024, seed=43, buses=11, fade=False), emit_strength=1.8, normal_strength=0.5)
    ctx.mat("mask", "porcelain mask", (0.78, 0.72, 0.62), metal=0.04, rough=0.34, coat=0.5, sheen=0.1,
            sheen_tint=(1, 0.95, 0.85))
    ctx.mat("cable", "braided conduit", (0.035, 0.03, 0.027), metal=0.7, rough=0.42)
    ctx.mat("rune", "rune halo band", (0.30, 0.22, 0.10), metal=0.85, rough=0.30)
    ctx.texture("rune", rune_strip_maps(RUNE_GLOW, base_rgb=(0.30, 0.22, 0.10), line_rgb=(0.55, 0.38, 0.14),
                                        w=1024, h=512, cols=2, aspect=1.6, seed=13), emit_strength=6.0,
                normal_strength=0.5)
    ctx.mat("runeB", "ivory rune halo", (0.86, 0.79, 0.64), metal=0.12, rough=0.30, coat=0.5)
    ctx.texture("runeB", rune_strip_maps(RUNE_GLOW, base_rgb=(0.82, 0.75, 0.60), line_rgb=(0.66, 0.46, 0.16),
                                         w=1024, h=512, cols=2, aspect=1.5, seed=29), emit_strength=5.5,
                normal_strength=0.5)
    ctx.mat("halo", "halo gold", (0.98, 0.80, 0.50), metal=1.0, rough=0.24)
    ctx.texture("halo", filigree_maps((0.98, 0.80, 0.50), (0.62, 0.44, 0.20), size=512, seed=44, density=10,
                                      width=1), normal_strength=0.40)
    ctx.mat("glow", "gem glow", (1.0, 0.88, 0.62), emit=(1.0, 0.82, 0.50), strength=6.5)
    ctx.mat("charge", "charge core glow", (1.0, 0.78, 0.40), emit=(1.0, 0.66, 0.24), strength=3.4)
    ctx.mat("sun", "sun core glow", (1.0, 0.80, 0.45), emit=(1.0, 0.70, 0.30), strength=4.0)
    ctx.texture("sun", sunburst_maps((1.0, 0.72, 0.32), (0.95, 0.72, 0.40), rays=16, size=512), emit_strength=4.5,
                normal_strength=0.0)
    ctx.mat("inlay", "gold light inlay", (0.60, 0.48, 0.28), emit=ACCENT, strength=3.8)
    # 光束 / 炮口光晕：半透明图集材质（外层光晕 + 内层编织光晕 + 白金芯线 + 脉冲环 + 圆盘光斑），强度 <= 2.5
    M["beam"] = FX.beam_material(f"{ctx.title} emitter beam glow")
    return M


# ===== 布局常量（右侧 +X；左侧镜像） =====
HC = Vector((0, 0.16, 5.22))                       # 头部中心
HEAD_RX, HEAD_RY = 0.27, 0.30
SUN_Z = 4.12
TILT = math.radians(12)
HALO_C = Vector((0, -1.22, 5.12))                  # 光环中心
HN = Vector((0, math.cos(TILT), math.sin(TILT)))   # 环面法向（朝前上，便于俯视镜头看到环面）
HU = Vector((1, 0, 0))
HV = Vector((0, -math.sin(TILT), math.cos(TILT)))  # 环面内的“上”
RINGS = {"A": (0.10, 0.64, 0.88), "B": (0.0, 1.12, 1.40), "C": (-0.10, 1.56, 1.72)}   # (法向偏移, 内径, 外径)
RING_SYM = math.radians(30)                        # 光环 12 重对称步进角
STRUT_BASE = Vector((0, -0.54, 4.52))

ARMS = {
    1: dict(S=(0.97, -0.12, 4.56), E=(1.68, -0.20, 5.08), W=(2.00, 0.02, 5.84), rho=0.155, kind="emitter",
            size=1.0, d=(0.36, 0.30, 0.88), up=(1.0, -0.3, 0.2)),
    2: dict(S=(1.04, 0.02, 4.14), E=(1.90, 0.10, 3.88), W=(2.52, 0.52, 3.82), rho=0.145, kind="hand",
            size=1.0, up=(0.2, -0.2, 1.0)),
    3: dict(S=(0.76, 0.20, 3.62), E=(1.33, 0.40, 3.06), W=(1.60, 0.92, 2.82), rho=0.125, kind="emitter",
            size=0.8, d=(0.30, 0.92, -0.26), up=(0.3, 0.0, 1.0)),
}
EMIT_LEN = 0.86                                    # 发射器（腕 → 炮口）长度（按 size 缩放）
BEAM_LEN = {1: 4.6, 2: 3.8, 3: 3.6}               # 各对光束的束长（旧版统一 5.4 m 的硬棍，缩短后靠渐隐收束）
HALO_R = 0.34                                      # 炮口充能光晕半径（按 size 缩放；Muzzle 骨再按蓄能量缩放）

LAME_K, LAME_J = 10, 4
LAME_OUT = (0.0, 0.14, 0.23, 0.27, 0.27)
LAME_SEG = (0.44, 0.43, 0.41, 0.38)
CABLE_GAPS = (1, 2, 3, 4, 6, 7, 8, 9)
KEEL = [Vector((0, 0.03, 2.70)), Vector((0, 0.04, 2.16)), Vector((0, 0.05, 1.66)), Vector((0, 0.05, 1.20)),
        Vector((0, 0.05, 0.52))]


def arm_pts(n, side):
    A = ARMS[n]
    return mirror(A["S"], side), mirror(A["E"], side), mirror(A["W"], side)


def emit_dir(n, side):
    return mirror(ARMS[n]["d"], side).normalized()


def rest_pole(n, side):
    S, E, W = arm_pts(n, side)
    d = (W - S).normalized()
    p = E - S
    return (p - d * p.dot(d)).normalized()


def hand_frame(side):
    """中对机械手的静止标架：W 腕、pn 掌心朝向、fd 手指方向、sd 指向拇指（身体内侧）。"""
    W = arm_pts(2, side)[2]
    pn = Vector((0.28 * side, 0.94, 0.18)).normalized()
    fd = Vector((0.30 * side, -0.05, 1.0))
    fd = (fd - pn * fd.dot(pn)).normalized()
    sd = fd.cross(pn).normalized() * side
    return W, pn, fd, sd


FINGERS = [  # (名, 指根沿 fd 的位置, 沿 sd 的偏移, 张开角, 两节长度)
    ("F0", 0.13, 0.155, 0.0, (0.13, 0.11)),   # 拇指（另算方向）
    ("F1", 0.37, 0.095, 0.10, (0.16, 0.13)),
    ("F2", 0.38, 0.0, 0.0, (0.18, 0.145)),
    ("F3", 0.36, -0.095, -0.12, (0.15, 0.12)),
]


def finger_rest(side):
    """每根手指的静止关键点：[(名, 指根, 指中, 指尖, 弯曲轴)]。"""
    W, pn, fd, sd = hand_frame(side)
    out = []
    for name, along, off, spread, (la, lb) in FINGERS:
        base = W + fd * along + sd * off
        if name == "F0":
            d = (sd * 0.72 + fd * 0.62 + pn * 0.30).normalized()
        else:
            d = (fd + sd * spread).normalized()
        ax = d.cross(pn).normalized()
        mid = base + d * la
        d2 = Matrix.Rotation(0.18, 3, ax) @ d
        tip = mid + d2 * lb
        out.append((name, base, mid, tip, ax))
    return out


# ===== 躯干 =====
TORSO = [(4.66, 0.34, 0.28, 0.00), (4.60, 0.60, 0.40, -0.01), (4.52, 0.86, 0.50, -0.01), (4.40, 0.95, 0.55, 0.01),
         (4.22, 0.94, 0.58, 0.04), (4.02, 0.86, 0.58, 0.05), (3.84, 0.76, 0.54, 0.05), (3.70, 0.68, 0.50, 0.04),
         (3.52, 0.63, 0.48, 0.03)]
TORSO_K = [(z, (rx, ry, yo)) for z, rx, ry, yo in reversed(TORSO)]


def torso_relief(a, z, rx):
    front = max(0.0, math.cos(a))
    back = max(0.0, -math.cos(a))
    x = rx * math.sin(a)
    pec = 0.055 * gauss(z, 4.25, 0.12) * gauss(abs(x), 0.40, 0.20) * front ** 1.2
    recess = -0.045 * math.exp(-(x * x + (z - SUN_Z) ** 2) / 0.17 ** 2) * front ** 2
    keel = 0.014 * gauss(x, 0, 0.035) * front ** 3 * (1 - gauss(z, SUN_Z, 0.22))
    plates = 0.016 * front ** 2 * gauss(z, 3.72, 0.07) * (1 - gauss(x, 0, 0.05))
    blade = 0.035 * back * gauss(z, 4.30, 0.14) * gauss(abs(x), 0.38, 0.16)
    return pec + recess + keel + plates + blade


def torso_point(a, z, grow=0.0):
    rx, ry, yo = interp(TORSO_K, z)
    rel = torso_relief(a, z, rx)
    return Vector(((rx + grow + rel) * math.sin(a), yo + (ry + grow + rel) * math.cos(a), z))


def torso_top(a):
    return 4.66 - 0.05 * max(0.0, math.cos(a)) ** 4


def torso_bottom(a):
    return 3.56 - 0.10 * max(0.0, math.cos(a)) ** 3


def build_torso(ctx, M):
    def pt(u, v):
        a = u * TAU
        return torso_point(a, lerp(torso_top(a), torso_bottom(a), v))
    body = surface(f"{ctx.title} cuirass", pt, 72, 40, [M["ivory"]], closed_u=True,
                   uvfn=lambda u, v: (u * 4, (1 - v) * 1.1))
    orient(body, lambda c: Vector((0, 0.03, c.z)))
    ctx.part(body, invdist(["Pelvis", "Spine", "Chest"], 0.25))
    for name, zf, r in (("neckline", torso_top, 0.022), ("hem", torso_bottom, 0.024)):
        pts = [torso_point(i / 56 * TAU, zf(i / 56 * TAU), 0.006) for i in range(56)]
        ctx.part(trim(f"{ctx.title} cuirass {name}", pts, r, M["trim"], closed=True), invdist(["Spine", "Chest"], 0.25))
    # 胸骨金棱：从太阳核心向上到领口、向下到 V 口
    for z0, z1 in ((SUN_Z + 0.27, 4.60), (SUN_Z - 0.27, torso_bottom(0.0) + 0.02)):
        pts = [torso_point(0.0, lerp(z0, z1, i / 10), 0.004) for i in range(11)]
        ctx.part(trim(f"{ctx.title} sternum {z0:.2f}", pts, 0.016, M["trim"]), invdist(["Spine", "Chest"], 0.25))
    # 胸甲光缝：由核心向两肩与两肋展开的电路纹
    proj = projector(body, (0, -1, 0))
    lines = [[(0.27, 4.21), (0.37, 4.31), (0.53, 4.31), (0.64, 4.42)],
             [(0.27, 4.04), (0.40, 3.97), (0.56, 3.97), (0.66, 3.88)],
             [(0.10, 3.87), (0.10, 3.76), (0.24, 3.70), (0.42, 3.70)],
             [(0.19, 4.29), (0.23, 4.43), (0.34, 4.53)]]
    for side, label in SIDES:
        for i, ln in enumerate(lines):
            pts = densify([Vector((side * x, 0.6, z)) for x, z in ln], 0.03)
            pts = [proj(p, 0.006) for p in pts]
            ctx.part(trim(f"{ctx.title} chest inlay {label}{i}", pts, 0.010, M["inlay"]), invdist(["Spine", "Chest"], 0.25))
            end = pts[-1]
            ctx.part(ellipsoid(f"{ctx.title} chest via {label}{i}", end, (0.018, 0.018, 0.018), [M["glow"]], 8, 5),
                     invdist(["Spine", "Chest"], 0.25))
    # 腹部机械：深色棱纹筒 + 金箍
    def abd(u, v):
        a = u * TAU
        z = lerp(3.80, 3.06, v)
        t = (z - 3.06) / 0.74
        rib = 0.024 * (0.5 + 0.5 * math.cos((z - 3.08) / 0.14 * TAU))
        return Vector(((lerp(0.50, 0.62, t) + rib) * math.sin(a), 0.03 + (lerp(0.41, 0.49, t) + rib) * math.cos(a), z))
    belly = surface(f"{ctx.title} abdomen", abd, 56, 36, [M["dark"]], closed_u=True,
                    uvfn=lambda u, v: (u * 3, (1 - v) * 0.8))
    orient(belly, lambda c: Vector((0, 0.03, c.z)))
    ctx.part(belly, invdist(["Pelvis", "Spine"], 0.20))
    for z in (3.36, 3.50):
        t = (z - 3.06) / 0.74
        rx, ry = lerp(0.50, 0.62, t) + 0.034, lerp(0.41, 0.49, t) + 0.034
        pts = [Vector((rx * math.sin(i / 48 * TAU), 0.03 + ry * math.cos(i / 48 * TAU), z)) for i in range(48)]
        ctx.part(trim(f"{ctx.title} abdomen rib {z}", pts, 0.018, M["trim"], closed=True), invdist(["Pelvis", "Spine"], 0.2))
    # 颈与金领
    neck = tube(f"{ctx.title} neck", [(0, 0.05, 4.48), (0, 0.08, 4.76), (0, 0.11, 5.02)], [0.21, 0.19, 0.17],
                [M["dark"]], n=18, per=4)
    ctx.part(neck, invdist(["Chest", "Neck", "Head"], 0.12))
    for z in (4.76, 4.84, 4.92):
        ctx.part(trim(f"{ctx.title} neck ring {z}", circle((0, 0.05 + (z - 4.48) * 0.12, z), X, Y, 0.20 - (z - 4.76) * 0.2, 28),
                      0.016, M["trim"], closed=True), rigid("Neck"))
    collar = lathe(f"{ctx.title} gorget", [(0.52, 4.60), (0.47, 4.67), (0.37, 4.75), (0.27, 4.79)], [M["ivory"]],
                   segments=56, center=(0, 0.0, 0), sy=0.84)
    ctx.part(finish(collar, 0.02, -1, 0), invdist(["Chest", "Neck"], 0.1))
    ctx.part(trim(f"{ctx.title} gorget rim", [Vector((0.52 * math.sin(a), 0.44 * math.cos(a), 4.60))
                                              for a in [i / 48 * TAU for i in range(48)]], 0.02, M["trim"], closed=True),
             rigid("Chest"))
    ctx.part(trim(f"{ctx.title} gorget lip", [Vector((0.27 * math.sin(a), 0.227 * math.cos(a), 4.79))
                                              for a in [i / 36 * TAU for i in range(36)]], 0.014, M["trim"], closed=True),
             invdist(["Chest", "Neck"], 0.1))
    return body


def build_sun(ctx, M):
    """胸口太阳核心：金框 + 发光日盘（挂 Sun 骨，可缩放爆亮）+ 16 道贴合胸甲的金色光芒。"""
    body = ctx.marks["torso"]
    c = torso_point(0.0, SUN_Z) + Vector((0, 0.01, 0))
    ctx.marks["sun"] = c
    ctx.part(trim(f"{ctx.title} sun frame", circle(c, X, Z, 0.24, 40), 0.032, M["trim"], closed=True), rigid("Chest"))
    ctx.part(trim(f"{ctx.title} sun iris", circle(c + Vector((0, 0.03, 0)), X, Z, 0.12, 36), 0.012, M["trim"], closed=True),
             rigid("Chest"))
    disc = lathe_y(f"{ctx.title} sun disc", [(0.0, 0.065), (0.07, 0.060), (0.14, 0.045), (0.20, 0.012), (0.205, -0.01),
                                             (0.16, -0.03), (0.0, -0.035)], [M["sun"]], seg=32, uv=lambda u, v: (u, 1 - v * 1.6))
    place(disc, c, (0, 1, 0), up=(0, 0, 1))
    ctx.part(disc, rigid("Sun"))
    ctx.part(ellipsoid(f"{ctx.title} sun heart", c + Vector((0, 0.05, 0)), (0.06, 0.03, 0.06), [M["glow"]], 12, 8),
             rigid("Chest"))
    proj = projector(body, (0, -1, 0))
    for i in range(16):
        phi = i / 16 * TAU
        rr = Vector((math.sin(phi), 0, math.cos(phi)))
        pp = Vector((math.cos(phi), 0, -math.sin(phi)))
        L = 0.30 if i % 2 == 0 else 0.17
        w0 = 0.07 if i % 2 == 0 else 0.05

        def fn(u, v, rr=rr, pp=pp, L=L, w0=w0):
            rho = 0.27 + L * v
            q = c + rr * rho + pp * ((u - 0.5) * w0 * (1 - v) ** 1.2)
            return proj(Vector((q.x, 0.8, q.z)), 0.010)
        ray = grid(f"{ctx.title} sun ray {i}", fn, lin(0, 1, 3), lin(0, 1, 6), [M["trim"]])
        ctx.part(finish(ray, 0.012, 0, 0), invdist(["Spine", "Chest"], 0.25))


def build_back(ctx, M):
    """背部：连接两肩的金色轭架、脊背反应舱与光缝、托起光环的脊柱支架（Mandorla 骨）。"""
    yoke = [(-0.92, -0.30, 4.48), (-0.52, -0.52, 4.62), (0, -0.60, 4.66), (0.52, -0.52, 4.62), (0.92, -0.30, 4.48)]
    ctx.part(tube(f"{ctx.title} yoke", yoke, [0.06, 0.075, 0.085, 0.075, 0.06], [M["gold"]], n=12, per=4), rigid("Chest"))
    pod = lathe_y(f"{ctx.title} spine pod", [(0.0, -0.02), (0.12, 0.0), (0.17, 0.10), (0.18, 0.40), (0.16, 0.66),
                                               (0.10, 0.74), (0.0, 0.76)], [M["ivory"]], seg=24)
    place(pod, (0, -0.55, 3.82), (0, 0.02, 1), up=(0, -1, 0))
    ctx.part(pod, rigid("Chest"))
    for k, h in enumerate((0.16, 0.38, 0.60)):
        ctx.part(trim(f"{ctx.title} pod ring {k}", circle((0, -0.55, 3.82 + h), X, Y, 0.185, 28), 0.016, M["trim"],
                      closed=True), rigid("Chest"))
    for sd in (-1, 1):
        pts = [Vector((sd * 0.07, -0.55 - 0.176, 3.82 + h)) for h in lin(0.20, 0.56, 6)]
        ctx.part(trim(f"{ctx.title} pod slit {sd}", pts, 0.012, M["inlay"]), rigid("Chest"))
    # 脊柱支架：从背上端伸向光环中心
    end = HALO_C - HN * 0.06
    d = end - STRUT_BASE
    L = d.length
    strut = lathe_y(f"{ctx.title} strut", [(0.10, 0.0), (0.14, 0.08), (0.11, 0.30 * L), (0.085, 0.70 * L),
                                             (0.075, 0.94 * L), (0.10, L)], [M["ivory"]], seg=20)
    place(strut, STRUT_BASE, d, up=(0, 0, 1))
    ctx.part(strut, rigid("Mandorla"))
    for t in (0.12, 0.45, 0.78):
        ctx.part(trim(f"{ctx.title} strut ring {t}", ring_around(STRUT_BASE, end, t, 0.125 - 0.04 * t, 24), 0.016,
                      M["trim"], closed=True), rigid("Mandorla"))
    # 光环轴心（静止在支架上）：金玫瑰盘 + 发光核 + 八根辐条
    hub = lathe_y(f"{ctx.title} halo hub", [(0.0, 0.07), (0.14, 0.065), (0.26, 0.04), (0.34, 0.01), (0.36, -0.02),
                                              (0.30, -0.05), (0.0, -0.06)], [M["halo"]], seg=36)
    place(hub, HALO_C, HN, up=HV)
    ctx.part(hub, rigid("Mandorla"))
    ctx.part(ellip(f"{ctx.title} hub core", HALO_C + HN * 0.075, (0.12, 0.12, 0.03), (HU, HV, HN), [M["glow"]], 20, 10),
             rigid("Mandorla"))
    ctx.part(trim(f"{ctx.title} hub ring", circle(HALO_C + HN * 0.02, HU, HV, 0.45, 48), 0.012, M["inlay"], closed=True),
             rigid("Mandorla"))
    for k in range(8):
        a = k / 8 * TAU + TAU / 16
        ctx.part(spike(f"{ctx.title} hub spoke {k}", ring_at(HALO_C, HU, HV, 0.30, a), ring_at(HALO_C, HU, HV, 0.58, a),
                       0.03, [M["halo"]], sides=4, fx=1.0, fy=0.5, up=HN), rigid("Mandorla"))
    # 肩后扇形翼饰（挂胸骨，不随上臂转动）
    for side, label in SIDES:
        base = Vector((side * 0.76, -0.40, 4.58))
        for k, (L, w) in enumerate(((0.95, 0.25), (0.80, 0.22), (0.62, 0.18))):
            f = Vector((side * (0.55 + 0.35 * k), -0.58, 1.0 - 0.22 * k)).normalized()
            lat = Y.cross(f).normalized()
            nrm = lat.cross(f).normalized()

            def fn(u, v, f=f, lat=lat, nrm=nrm, L=L, w=w, k=k):
                s = 2 * u - 1
                width = w * math.sin(math.pi * min(1.0, 0.12 + v * 0.95)) ** 0.8 * (1 - 0.55 * v)
                return base + f * (L * v) + lat * (s * width * 0.5) + nrm * (0.03 * (1 - s * s) + 0.05 * math.sin(math.pi * v)) \
                    + Vector((0, -0.05 * k, 0))
            us = [0, 0.08, 0.3, 0.5, 0.7, 0.92, 1.0]
            fl = grid(f"{ctx.title} shoulder flare {label}{k}", fn, us, lin(0, 1, 9), [M["ivory"], M["gold"]],
                      matfn=lambda i, j: 1 if i in (0, 5) else 0, uvfn=lambda u, v: (u * 0.4, v * 0.8))
            ctx.part(finish(fl, 0.03, 0, 0), rigid("Chest"))
            pts = [fn(0.5, v) + nrm * 0.02 for v in lin(0.12, 0.85, 8)]
            ctx.part(trim(f"{ctx.title} flare seam {label}{k}", pts, 0.011, M["inlay"]), rigid("Chest"))


# ===== 头部：闭目瓷面具 + 金盔 + 扇形光冠 =====
HS = 1.12                                          # 头部整体放大（面部特征按基准头定义，再乘 HS）
HEAD_PROF = [(0.00, (0.03, 0.40)), (0.10, (0.46, 0.385)), (0.24, (0.80, 0.31)), (0.40, (0.96, 0.17)),
             (0.54, (1.00, 0.03)), (0.66, (0.95, -0.10)), (0.78, (0.78, -0.22)), (0.88, (0.54, -0.31)),
             (0.95, (0.34, -0.355)), (1.00, (0.03, -0.37))]


def face_relief(x, z):
    """面具浮雕（基准头坐标：x 横向、z 相对头心的高度，单位米）。"""
    ax = abs(x)
    r = 0.0
    r += 0.034 * gauss(z, 0.095, 0.030) * (1 - smoothstep(0.14, 0.21, ax))              # 眉弓
    r -= 0.030 * gauss(ax, 0.092, 0.045) * gauss(z, 0.035, 0.030)                         # 眼窝
    r += 0.015 * gauss(ax, 0.092, 0.040) * gauss(z, 0.030, 0.014)                         # 闭合眼睑（杏仁形隆起）
    t = smoothstep(0.08, -0.09, z)
    nose = (0.018 + 0.064 * t) * smoothstep(-0.125, -0.095, z) * (1 - smoothstep(0.08, 0.12, z))
    r += nose * gauss(x, 0, 0.018 + 0.012 * t)                                            # 鼻梁到鼻尖
    r += 0.018 * gauss(z, -0.112, 0.012) * gauss(ax, 0.030, 0.016)                        # 鼻翼
    r -= 0.010 * gauss(z, -0.150, 0.014) * gauss(ax, 0.010, 0.008)                        # 人中
    r += 0.020 * gauss(z, -0.182, 0.011) * gauss(x, 0, 0.050)                             # 上唇
    r += 0.017 * gauss(z, -0.218, 0.012) * gauss(x, 0, 0.042)                             # 下唇
    r -= 0.010 * gauss(z, -0.200, 0.004) * gauss(x, 0, 0.050)                             # 唇缝
    r -= 0.010 * gauss(z, -0.245, 0.010) * gauss(x, 0, 0.05)                              # 唇下凹
    r += 0.036 * gauss(z, -0.290, 0.032) * gauss(x, 0, 0.070)                             # 下巴
    r += 0.016 * gauss(ax, 0.13, 0.05) * gauss(z, -0.09, 0.05)                            # 颧骨
    r -= 0.012 * gauss(ax, 0.15, 0.04) * gauss(z, -0.17, 0.05)                            # 颊下凹
    return r


def head_angle(u):
    """把 u 映射到绕头角度：正面列更密（面部细节），脑后更疏。"""
    s = 2 * u - 1
    return math.pi * (0.45 * s + 0.55 * s ** 3)


def head_point(a, v, grow=0.0):
    r, dz = interp(HEAD_PROF, v)
    x = HEAD_RX * r * math.sin(a)
    y = HEAD_RY * r * math.cos(a)
    front = max(0.0, math.cos(a))
    y += face_relief(x, dz) * front ** 1.5 - 0.02 * front ** 4 * r   # 正面略压平成面具
    p = Vector((x, y, dz))
    if grow:
        p += Vector((x / HEAD_RX, y / HEAD_RY, dz / 0.39)).normalized() * (grow / HS)
    return HC + p * HS


def face_at(x, dz):
    """基准头坐标 (x, 相对高度) → 世界坐标里的投射起点（在脸前方）。"""
    return HC + Vector((x, 1.0, dz)) * HS


def build_head(ctx, M):
    face = surface(f"{ctx.title} mask", lambda u, v: head_point(head_angle(u), v), 88, 64, [M["mask"]], closed_u=True)
    orient(face, lambda c: HC)
    ctx.part(face, rigid("Head"))
    proj = projector(face, (0, -1, 0))
    for side in (-1, 1):
        # 闭合的双眼：向下弯的发光睑缝 + 其上的金色睑线
        eye = [proj(face_at(side * x, 0.030 - 0.013 * (1 - ((x - 0.095) / 0.060) ** 2)), 0.002)
               for x in lin(0.038, 0.155, 14)]
        ctx.part(tube(f"{ctx.title} eye {side}", eye, [0.004] + [0.0085] * 12 + [0.004], [M["glow"]], n=5, per=1),
                 rigid("Head"))
        lid = [proj(face_at(side * x, 0.040 - 0.006 * (1 - ((x - 0.095) / 0.060) ** 2)), 0.003)
               for x in lin(0.045, 0.150, 10)]
        ctx.part(trim(f"{ctx.title} lid {side}", lid, 0.006, M["trim"]), rigid("Head"))
        # 长弧眉（金丝），从鼻根挑向太阳穴
        brow_l = [proj(face_at(side * x, 0.080 + 0.024 * math.sin(math.pi * (x - 0.02) / 0.19)), 0.003)
                  for x in lin(0.022, 0.185, 12)]
        ctx.part(trim(f"{ctx.title} brow {side}", brow_l, 0.0075, M["trim"]), rigid("Head"))
    lips = [proj(face_at(x, -0.200 + 0.006 * (1 - (x / 0.05) ** 2)), 0.002) for x in lin(-0.05, 0.05, 11)]
    ctx.part(trim(f"{ctx.title} lips", lips, 0.0045, M["trim"]), rigid("Head"))
    # 额心第三眼：竖向发光杏核 + 金色菱框
    brow = proj(face_at(0, 0.185), 0.004)
    ctx.part(ellip(f"{ctx.title} third eye", brow, (0.018, 0.040, 0.010), (X, Z, Y), [M["glow"]], 12, 8), rigid("Head"))
    frame = [brow + Vector((0.0, 0.006, 0.072)), brow + Vector((0.040, 0.006, 0.0)), brow + Vector((0.0, 0.006, -0.066)),
             brow + Vector((-0.040, 0.006, 0.0))]
    ctx.part(trim(f"{ctx.title} third eye frame", densify(frame + [frame[0]], 0.02)[:-1], 0.007, M["trim"], closed=True),
             rigid("Head"))
    # 金盔：盖住头顶与脑后，正面到发际线
    def v_edge(a):
        return lerp(0.25, 0.86, smoothstep(0.75, 1.6, abs(a)))

    def helm_pt(u, v):
        a = (u - 0.5) * TAU
        return head_point(a, v * v_edge(a), 0.022)
    helm = surface(f"{ctx.title} helm", helm_pt, 72, 16, [M["gold"]], closed_u=True,
                   uvfn=lambda u, v: (u * 1.5, (1 - v) * 0.5))
    orient(helm, lambda c: HC)
    ctx.part(finish(helm, 0.016, -1, 0), rigid("Head"))
    rim = [helm_pt(i / 56, 1.0) for i in range(56)]
    ctx.part(trim(f"{ctx.title} helm rim", rim, 0.014, M["trim"], closed=True), rigid("Head"))
    diadem = [head_point((i / 24 - 0.5) * 2.1, 0.30, 0.026) for i in range(25)]
    ctx.part(trim(f"{ctx.title} diadem", diadem, 0.010, M["inlay"]), rigid("Head"))
    # 耳盘
    for side in (-1, 1):
        c = HC + Vector((side * (HEAD_RX + 0.025), -0.02, -0.01)) * HS
        disc = lathe_y(f"{ctx.title} ear disc {side}", [(0.0, 0.05), (0.08, 0.045), (0.12, 0.02), (0.125, 0.0),
                                                       (0.10, -0.03), (0.0, -0.03)], [M["gold"]], seg=28)
        place(disc, c, (side, 0, 0), up=(0, 0, 1))
        ctx.part(disc, rigid("Head"))
        ctx.part(trim(f"{ctx.title} ear ring {side}", circle(c + Vector((side * 0.05, 0, 0)), Y, Z, 0.085, 28), 0.008,
                      M["inlay"], closed=True), rigid("Head"))
        ctx.part(ellipsoid(f"{ctx.title} ear gem {side}", c + Vector((side * 0.052, 0, 0)), (0.012, 0.035, 0.035),
                           [M["glow"]], 12, 8), rigid("Head"))
    # 扇形光冠：七片刃羽由盔顶向外放射（略后仰）
    for i in range(7):
        th = math.radians(-72 + 24 * i)
        bdir = Vector((math.sin(th), -0.36 * math.cos(th) - 0.10, math.cos(th))).normalized()
        base = HC + (Vector((0, -0.04, 0.02)) + Vector((bdir.x * HEAD_RX, bdir.y * HEAD_RY, bdir.z * 0.39)) * 0.92) * HS
        L = 0.66 * (1 - 0.42 * (th / math.radians(72)) ** 2)
        lat = Vector((math.cos(th), 0, -math.sin(th)))
        nrm = lat.cross(bdir).normalized()

        def fn(u, v, bdir=bdir, lat=lat, nrm=nrm, L=L, base=base):
            s = 2 * u - 1
            w = 0.10 * (1 - v ** 1.6) * (0.7 + 0.3 * math.sin(math.pi * min(1, v * 1.6)))
            return base + bdir * (L * v) + lat * (s * w * 0.5) + nrm * (0.012 * (1 - s * s))
        us = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        blade = grid(f"{ctx.title} crown blade {i}", fn, us, lin(0, 1, 8), [M["ivory"], M["gold"]],
                     matfn=lambda i_, j: 1 if i_ in (0, 5) else 0, uvfn=lambda u, v: (u * 0.2, v * 0.5))
        ctx.part(finish(blade, 0.018, 0, 0), rigid("Head"))
        ctx.part(trim(f"{ctx.title} crown seam {i}", [fn(0.5, v) + nrm * 0.013 for v in lin(0.08, 0.80, 7)], 0.006,
                      M["inlay"]), rigid("Head"))
        ctx.part(ellipsoid(f"{ctx.title} crown tip {i}", base + bdir * (L * 1.02), (0.02,) * 3, [M["glow"]], 8, 5), rigid("Head"))


# ===== 手臂 =====
def build_arm(ctx, M, n, side, label):
    A = ARMS[n]
    S, E, W = arm_pts(n, side)
    rho = A["rho"]
    up = mirror(A["up"], side)
    upper, fore = f"Arm{n}.{label}", f"Fore{n}.{label}"
    T = ctx.title

    def upper_r(t, phi):
        base = interp([(0.10, 0.62), (0.18, 0.96), (0.38, 1.0), (0.62, 0.92), (0.80, 0.80), (0.88, 0.72)], t)
        ridge = 0.20 * math.exp(-(math.atan2(math.sin(phi), math.cos(phi)) / 0.32) ** 2) * math.sin(math.pi * clamp01((t - 0.12) / 0.74))
        return rho * (base + ridge + 0.035 * math.cos(6 * phi))

    def fore_r(t, phi):
        base = interp([(0.08, 0.60), (0.25, 0.80), (0.55, 0.86), (0.82, 0.95), (0.93, 1.02)], t)
        ridge = 0.14 * math.exp(-(math.atan2(math.sin(phi), math.cos(phi)) / 0.30) ** 2) * math.sin(math.pi * clamp01((t - 0.10) / 0.80))
        return rho * 0.95 * (base + ridge + 0.03 * math.cos(6 * phi))
    for nm, a, b, rf, t0, t1, bone in (("upper", S, E, upper_r, 0.10, 0.88, upper), ("fore", E, W, fore_r, 0.08, 0.93, fore)):
        shell = sweep(f"{T} arm {nm} {n}{label}", a, b, rf, [M["ivory"]], nu=28, nv=12, up=up, t0=t0, t1=t1,
                      uv=(1.0, (b - a).length))
        ctx.part(shell, rigid(bone))
        ctx.part(tube(f"{T} arm core {nm} {n}{label}", [a, b], [rho * 0.46, rho * 0.42], [M["dark"]], n=10, per=1),
                 rigid(bone))
        x, z = axis_frame((b - a).normalized(), up)
        dn = (b - a).normalized()
        L = (b - a).length
        ridge = [a + dn * (t * L) + z * (rf(t, 0.0) + 0.010) for t in lin(t0 + 0.08, t1 - 0.08, 10)]
        ctx.part(trim(f"{T} arm seam {nm} {n}{label}", ridge, 0.011, M["inlay"]), rigid(bone))
        for t in (t0 + 0.03, t1 - 0.03):
            rr = max(rf(t, math.pi / 2), rf(t, math.pi)) + 0.012
            ctx.part(trim(f"{T} arm ring {nm} {n}{label} {t:.2f}", ring_around(a, b, t, rr, 20, up), 0.016,
                          M["trim"], closed=True), rigid(bone))
    cuff = sweep(f"{T} cuff {n}{label}", E, W, lambda t, phi: rho * 1.06, [M["gold"]], nu=28, nv=3, up=up,
                 t0=0.86, t1=0.97)
    ctx.part(finish(cuff, 0.012, 1, 0), rigid(fore))
    ctx.part(ellipsoid(f"{T} shoulder ball {n}{label}", S, (rho * 1.15,) * 3, [M["gold"]], 20, 12), rigid(upper))
    ctx.part(ellipsoid(f"{T} elbow ball {n}{label}", E, (rho * 0.84,) * 3, [M["gold"]], 18, 10), rigid(fore))
    ctx.part(ellipsoid(f"{T} wrist ball {n}{label}", W, (rho * 0.64,) * 3, [M["gold"]], 16, 10), rigid(fore))
    if n in (2, 3):
        # 胸侧关节座：金环
        d0 = (E - S).normalized()
        c = S - d0 * rho * 0.35
        x, z = axis_frame(d0, (0, 0, 1))
        pts = [c + (x * math.cos(TAU * i / 24) + z * math.sin(TAU * i / 24)) * rho * 1.32 for i in range(24)]
        ctx.part(trim(f"{T} socket {n}{label}", pts, 0.028, M["trim"], closed=True), rigid("Chest" if n == 2 else "Spine"))
    if n == 1:
        # 护肩：三层外翻的扇形甲片（随上臂）
        for k in range(3):
            t0, t1 = -0.14 + 0.12 * k, 0.08 + 0.12 * k
            r0, r1 = 0.20 - 0.005 * k, 0.31 - 0.02 * k

            def pr(t, phi, t0=t0, t1=t1, r0=r0, r1=r1):
                v = (t - t0) / (t1 - t0)
                return lerp(r0, r1, v ** 0.8) * (1 + 0.06 * math.cos(phi))
            cap = sweep(f"{T} pauldron {label}{k}", S, E, pr, [M["ivory"], M["gold"]], nu=15, nv=5, up=up, t0=t0, t1=t1,
                        phi0=-2.2, phi1=2.2, matfn=lambda i, j: 1 if j == 3 else 0, uv=(0.8, 0.3))
            ctx.part(finish(cap, 0.022, 1, 0), rigid(upper))
        # 护肩顶的发光棱
        x, z = axis_frame((E - S).normalized(), up)
        dn = (E - S).normalized()
        pts = [S + dn * ((-0.12 + 0.34 * i / 7) * (E - S).length) + z * (0.24 + 0.06 * i / 7) for i in range(8)]
        ctx.part(trim(f"{T} pauldron crest {label}", pts, 0.012, M["inlay"]), rigid(upper))


def clamp01(x):
    return max(0.0, min(1.0, x))


def build_emitter(ctx, M, n, side, label):
    """光束发射器：深色炮尾、象牙炮身（三道金线圈 + 三片金鳍 + 光缝）、金色炮口冠与发光透镜。"""
    A = ARMS[n]
    k = A["size"]
    W = arm_pts(n, side)[2]
    d = emit_dir(n, side)
    up = Vector((0, 0, 1)) if abs(d.z) < 0.8 else Vector((0, -1, 0))
    hand = f"Hand{n}.{label}"
    T = ctx.title

    def lathe_at(name, prof, mat, seg=24):
        obj = lathe_y(name, [(r * k, y * k) for r, y in prof], [mat], seg=seg, uv=lambda u, v: (u * 1.0, v * 0.6))
        return place(obj, W, d, up)
    ctx.part(lathe_at(f"{T} breech {n}{label}", [(0.0, -0.06), (0.09, -0.05), (0.13, 0.0), (0.14, 0.10), (0.13, 0.17),
                                                   (0.11, 0.21)], M["dark"]), rigid(hand))
    ctx.part(lathe_at(f"{T} barrel {n}{label}", [(0.105, 0.19), (0.15, 0.25), (0.157, 0.40), (0.143, 0.62), (0.122, 0.71)],
                      M["ivory"], seg=28), rigid(hand))
    ctx.part(lathe_at(f"{T} muzzle {n}{label}", [(0.112, 0.68), (0.17, 0.74), (0.188, 0.80), (0.165, 0.865),
                                                   (0.118, 0.86), (0.10, 0.80)], M["gold"], seg=28), rigid(hand))
    lx, lz = axis_frame(d, up)
    lens = W + d * (0.815 * k)
    ctx.part(ellip(f"{T} lens {n}{label}", lens, (0.10 * k, 0.03 * k, 0.10 * k), (lx, d, lz), [M["glow"]], 16, 6),
             rigid(hand))
    for y in (0.30, 0.44, 0.58):
        c = W + d * (y * k)
        pts = [c + (lz * math.cos(TAU * i / 20) + lx * math.sin(TAU * i / 20)) * (0.166 * k) for i in range(20)]
        ctx.part(trim(f"{T} coil {n}{label} {y}", pts, 0.017 * k, M["trim"], closed=True), rigid(hand))
    for j in range(3):
        phi = j / 3 * TAU
        rad = lz * math.cos(phi) + lx * math.sin(phi)
        prof = [(0.0, 0.0), (0.10, 0.25), (0.46, 0.55), (0.47, 0.0)]
        outline = [(y * k, h * 0.13 * k) for y, h in [(0.22, 0.0), (0.30, 0.7), (0.52, 1.0), (0.66, 0.35), (0.70, 0.0)]]
        fin = plate(f"{T} fin {n}{label}{j}", outline, 0.022 * k, [M["gold"]], origin=W + rad * (0.15 * k), xaxis=d,
                    yaxis=rad, bev=0.004)
        ctx.part(fin, rigid(hand))
        phi2 = phi + TAU / 6
        rad2 = lz * math.cos(phi2) + lx * math.sin(phi2)
        pts = [W + d * (y * k) + rad2 * (lerp(0.151, 0.145, (y - 0.26) / 0.34) + 0.008) * k for y in lin(0.26, 0.60, 6)]
        ctx.part(trim(f"{T} barrel seam {n}{label}{j}", pts, 0.010 * k, M["inlay"]), rigid(hand))
    # 炮口莲瓣：六片金瓣外翻，给臂端一个华丽的冠形剪影
    for j in range(6):
        phi = (j + 0.5) / 6 * TAU
        rad = lz * math.cos(phi) + lx * math.sin(phi)
        pd = (d * math.cos(math.radians(38)) + rad * math.sin(math.radians(38))).normalized()
        tg = d.cross(rad).normalized()
        L, w = 0.19 * k, 0.085 * k
        outline = [(-w / 2, 0.0), (-w * 0.48, L * 0.35), (-w * 0.25, L * 0.75), (0.0, L), (w * 0.25, L * 0.75),
                   (w * 0.48, L * 0.35), (w / 2, 0.0)]
        ctx.part(plate(f"{T} petal {n}{label}{j}", outline, 0.012 * k, [M["gold"]], origin=W + d * (0.79 * k) + rad * (0.165 * k),
                       xaxis=tg, yaxis=pd, bulge=lambda x, y, w=w: -0.25 * (x / w) ** 2 * w, bev=0.002), rigid(hand))
    # 蓄能光球（Muzzle 骨缩放）与光束（Beam 骨缩放；独立命名节点，网页端可按名字隐藏 / 驱动）
    muzzle = W + d * (0.80 * k)
    ctx.part(ellipsoid(f"{T} charge {n}{label}", muzzle + d * (0.05 * k), (0.12 * k,) * 3, [M["charge"]], 14, 8),
             rigid(f"Muzzle{n}.{label}"))
    build_beam(ctx, M, n, label, muzzle, d, k)
    return muzzle


def build_beam(ctx, M, n, label, origin, d, k):
    """能量光束 + 炮口充能光晕。光束是独立命名节点（Beam 骨缩放驱动）；光晕蒙到 Muzzle 骨（随蓄能缩放），共用光束材质。"""
    ctx.part(FX.muzzle_halo(f"{ctx.title} muzzle halo {n}{label}", origin + d * (0.05 * k), d, HALO_R * k, M["beam"]),
             rigid(f"Muzzle{n}.{label}"))
    beam = FX.energy_beam(f"{ctx.ID}_BEAM_{n}{label}", origin, d, BEAM_LEN[n], k, M["beam"], seed=n + (0.5 if label == "R" else 0.0))
    beam.hide_render = True                  # --geo 审图里不显示（静止姿态下光束是全长）
    ctx.attach(beam, f"Beam{n}.{label}", keep=True)
    ctx.marks.setdefault("beams", []).append(beam)


def build_hand(ctx, M, side, label):
    """中对机械手：张掌结印（掌心朝前、四指向上），掌心发光透镜（Muzzle2 / Beam2）。"""
    W, pn, fd, sd = hand_frame(side)
    T = ctx.title
    hand = f"Hand2.{label}"

    def palm(u, v, lift=0.0, grow=0.0):
        s = 2 * u - 1
        width = (0.15 + grow) * (1 - 0.12 * v)
        return W + fd * (0.06 + (0.31 + grow) * v) + sd * (s * width) + pn * (lift - 0.028 * (1 - s * s) * math.sin(math.pi * v))
    us = [0, 0.08, 0.3, 0.5, 0.7, 0.92, 1.0]
    p = grid(f"{T} palm {label}", palm, us, lin(0, 1, 7), [M["ivory"], M["gold"]],
             matfn=lambda i, j: 1 if i in (0, 5) or j == 5 else 0, uvfn=lambda u, v: (u * 0.3, v * 0.3))
    orient(p, lambda c: c - pn)
    ctx.part(finish(p, 0.07, 0, 0), rigid(hand))
    back = grid(f"{T} hand back {label}", lambda u, v: palm(u, v, -0.05, 0.012), us, lin(0, 1, 5), [M["gold"]],
                uvfn=lambda u, v: (u * 0.3, v * 0.3))
    ctx.part(finish(back, 0.03, 0, 0), rigid(hand))
    lc = W + fd * 0.21 + pn * 0.030
    ctx.part(ellip(f"{T} palm lens {label}", lc, (0.075, 0.075, 0.022), (sd, fd, pn), [M["glow"]], 20, 8), rigid(hand))
    ctx.part(trim(f"{T} palm ring {label}", circle(lc, sd, fd, 0.092, 20), 0.012, M["trim"], closed=True), rigid(hand))
    for name, base, mid, tip, ax in finger_rest(side):
        ba, bb = f"{name}a.{label}", f"{name}b.{label}"
        for seg, a, b, bone, r in (("a", base, mid, ba, 0.043), ("b", mid, tip, bb, 0.036)):
            dvec = b - a
            L = dvec.length
            obj = lathe_y(f"{T} finger {name}{seg} {label}", [(0.0, 0.0), (r * 0.8, 0.012), (r, 0.04), (r * 0.92, L - 0.03),
                                                             (r * 0.6, L - 0.004), (0.0, L)], [M["ivory"]], seg=12)
            place(obj, a, dvec, up=pn)
            ctx.part(obj, rigid(bone))
            ctx.part(ellipsoid(f"{T} knuckle {name}{seg} {label}", a, (r * 1.08,) * 3, [M["gold"]], 12, 8),
                     rigid(bone if seg == "b" else hand))
        ctx.part(ellipsoid(f"{T} nail {name} {label}", tip - (tip - mid).normalized() * 0.02, (0.030,) * 3, [M["gold"]], 10, 6),
                 rigid(bb))
    muzzle = lc + pn * 0.02
    ctx.part(ellip(f"{T} palm charge {label}", muzzle, (0.10, 0.10, 0.06), (sd, fd, pn), [M["charge"]], 16, 10),
             rigid(f"Muzzle2.{label}"))
    build_beam(ctx, M, 2, label, muzzle, pn, 1.0)
    return muzzle


# ===== 光环 =====
def build_halo(ctx, M):
    T = ctx.title
    offA, a0, a1 = RINGS["A"]
    cA = HALO_C + HN * offA
    spec = rigid("HaloA")
    ctx.part(band(f"{T} halo A band", cA, HU, HV, a0, a1, [M["rune"]], seg=96, thick=0.05,
                  uv=lambda u, v: (u * 12, 1 - v)), spec)
    for r in (a0 - 0.004, a1 + 0.004):
        ctx.part(trim(f"{T} halo A rim {r:.2f}", circle(cA, HU, HV, r, 60), 0.02, M["trim"], closed=True), spec)
    for i in range(12):
        a = i / 12 * TAU
        ctx.part(ellipsoid(f"{T} halo A knob {i}", ring_at(cA, HU, HV, a1 + 0.045, a), (0.036,) * 3, [M["halo"]], 10, 6), spec)
    offB, b0, b1 = RINGS["B"]
    cB = HALO_C + HN * offB
    spec = rigid("HaloB")
    ctx.part(band(f"{T} halo B band", cB, HU, HV, b0, b1, [M["runeB"]], seg=144, thick=0.06,
                  uv=lambda u, v: (u * 24, 1 - v)), spec)
    for r in (b0 - 0.004, b1 + 0.004):
        ctx.part(trim(f"{T} halo B rim {r:.2f}", circle(cB, HU, HV, r, 84), 0.022, M["trim"], closed=True), spec)
    for i in range(12):
        a = (i + 0.5) / 12 * TAU
        ctx.part(spike(f"{T} halo B tooth {i}", ring_at(cB, HU, HV, b0 - 0.01, a), ring_at(cB, HU, HV, b0 - 0.14, a), 0.04,
                       [M["halo"]], sides=4, fx=1.0, fy=0.45, up=HN), spec)
        ctx.part(ellipsoid(f"{T} halo B node {i}", ring_at(cB, HU, HV, b1 + 0.05, a), (0.030,) * 3, [M["glow"]], 8, 4), spec)
    offC, c0, c1 = RINGS["C"]
    cC = HALO_C + HN * offC
    spec = rigid("HaloC")
    for i in range(12):
        a = i / 12 * TAU
        seg = band(f"{T} halo C seg {i}", cC, HU, HV, c0, c1, [M["halo"]], seg=10, thick=0.07, a0=a - 0.235, a1=a + 0.235,
                   nv=3, bulge=0.02)
        ctx.part(seg, spec)
        rm = (c0 + c1) / 2
        for lo, hi in ((a - 0.205, a - 0.055), (a + 0.055, a + 0.205)):
            arcp = [ring_at(cC, HU, HV, rm, lo + (hi - lo) * q / 6) + HN * 0.056 for q in range(7)]
            ctx.part(trim(f"{T} halo C seam {i} {lo:.2f}", arcp, 0.008, M["inlay"]), spec)
        ctx.part(ellip(f"{T} halo C gem {i}", ring_at(cC, HU, HV, (c0 + c1) / 2, a) + HN * 0.045, (0.036, 0.036, 0.016),
                       (HU, HV, HN), [M["glow"]], 8, 4), spec)
    for i in range(24):
        a = i / 24 * TAU
        L = 0.40 if i % 2 == 0 else 0.19
        ctx.part(spike(f"{T} halo C ray {i}", ring_at(cC, HU, HV, c1 - 0.02, a), ring_at(cC, HU, HV, c1 + L, a),
                       0.045 if i % 2 == 0 else 0.035, [M["halo"]], sides=4, fx=1.0, fy=0.45, up=HN), spec)
    ctx.part(trim(f"{T} halo C outer light", circle(cC, HU, HV, c1 + 0.10, 72), 0.011, M["inlay"], closed=True), spec)
    ctx.part(trim(f"{T} halo C inner light", circle(cC, HU, HV, c0 - 0.03, 72), 0.009, M["inlay"], closed=True), spec)


# ===== 下半身：腰环、机械盆、垂挂甲片、导管线缆、龙骨坠 =====
def lame_chain(k):
    a = (k + 0.5) / LAME_K * TAU
    rho = Vector((math.sin(a), math.cos(a), 0))
    f = 1.0 - 0.12 * math.cos(a)
    p0 = Vector((0.60 * math.sin(a), 0.03 + 0.50 * math.cos(a), 3.03))
    pts, z = [p0], 3.03
    for j in range(1, LAME_J + 1):
        z -= LAME_SEG[j - 1] * f
        pts.append(Vector((p0.x, p0.y, z)) + rho * LAME_OUT[j])
    return a, pts


def cable_chain(i, g):
    a = g / LAME_K * TAU
    rho = Vector((math.sin(a), math.cos(a), 0))
    f = 1.0 + 0.07 * math.sin(g * 2.3)
    top = Vector((0.46 * math.sin(a), 0.03 + 0.38 * math.cos(a), 2.90))
    pts, z = [top], 2.90
    for j, (L, out) in enumerate(zip((0.50, 0.52, 0.52, 0.46), (0.09, 0.14, 0.13, 0.08))):
        z -= L * f
        pts.append(Vector((top.x, top.y, z)) + rho * out)
    return a, pts


def build_lower(ctx, M):
    T = ctx.title
    # 腰环：金带 + 发光符文箍 + 上下滚边 + 正面日轮扣
    ctx.part(cyl_band(f"{T} girdle", (0, 0.03, 0), 0.60, 0.50, 3.22, 3.00, [M["gold"]], seg=72, thick=0.03, flare=0.04,
                      uv=lambda u, v: (u * 4, (1 - v) * 0.3)), rigid("Pelvis"))
    ctx.part(cyl_band(f"{T} girdle runes", (0, 0.03, 0), 0.622, 0.520, 3.15, 3.075, [M["rune"]], seg=72, thick=0.008,
                      flare=0.02, uv=lambda u, v: (u * 30, 1 - v)), rigid("Pelvis"))
    for z, rx, ry in ((3.22, 0.615, 0.515), (3.00, 0.64, 0.535)):
        pts = [Vector((rx * math.sin(a), 0.03 + ry * math.cos(a), z)) for a in [i / 56 * TAU for i in range(56)]]
        ctx.part(trim(f"{T} girdle rim {z}", pts, 0.02, M["trim"], closed=True), rigid("Pelvis"))
    buckle = Vector((0, 0.03 + 0.545, 3.11))
    disc = lathe_y(f"{T} buckle", [(0.0, 0.05), (0.08, 0.045), (0.13, 0.02), (0.14, 0.0), (0.12, -0.02), (0.0, -0.02)],
                   [M["gold"]], seg=28)
    place(disc, buckle, (0, 1, 0))
    ctx.part(disc, rigid("Pelvis"))
    ctx.part(ellip(f"{T} buckle gem", buckle + Vector((0, 0.05, 0)), (0.05, 0.02, 0.05), (X, Y, Z), [M["glow"]], 16, 8),
             rigid("Pelvis"))
    # 机械盆（倒穹顶）
    bowl = lathe(f"{T} pelvic bowl", [(0.60, 3.04), (0.56, 2.94), (0.46, 2.82), (0.30, 2.72), (0.14, 2.66), (0.02, 2.64)],
                 [M["dark"]], segments=48, center=(0, 0.03, 0), sy=0.84)
    ctx.part(bowl, rigid("Pelvis"))
    # 垂挂甲片：10 条 × 4 节（每节刚性挂在自己的链骨上）
    lames = []
    for k in range(LAME_K):
        a, pts = lame_chain(k)
        lames.append((a, pts))
        rho = Vector((math.sin(a), math.cos(a), 0))
        tang = Vector((math.cos(a), -math.sin(a), 0))
        for j in range(1, LAME_J + 1):
            p0, p1 = pts[j - 1], pts[j]
            dseg = (p1 - p0).normalized()
            top = p0 - dseg * 0.05
            bot = p1 + dseg * (0.09 if j < LAME_J else 0.0)
            nrm = tang.cross(dseg).normalized()
            if nrm.dot(rho) < 0:
                nrm = -nrm
            w_top = 0.37 - 0.035 * (j - 1)
            w_bot = w_top - 0.04
            inset = -0.022 * (j - 1)
            last = j == LAME_J

            def fn(u, v, top=top, bot=bot, nrm=nrm, dseg=dseg, w_top=w_top, w_bot=w_bot, inset=inset, last=last):
                s = 2 * u - 1
                w = lerp(w_top, w_bot, v)
                if last:
                    w *= max(0.04, 1 - smoothstep(0.35, 1.0, v) ** 1.1)
                p = top.lerp(bot, v) + tang * (s * w * 0.5)
                p += dseg * (0.05 * (1 - s * s) * v * (0.0 if last else 1.0))
                bul = 0.04 * (1 - s * s) + 0.012 * math.exp(-(s / 0.18) ** 2) + inset
                return p + nrm * bul
            us = [0, 0.07, 0.2, 0.35, 0.5, 0.65, 0.8, 0.93, 1.0]
            vs = [0, 0.1, 0.3, 0.5, 0.7, 0.88, 1.0]
            obj = grid(f"{T} lame {k}.{j}", fn, us, vs, [M["ivory"], M["gold"]],
                       matfn=lambda i, jj, last=last: 1 if i in (0, 7) or (jj == 5 and not last) else 0,
                       uvfn=lambda u, v: (u * 0.45, v * 0.5))
            orient(obj, lambda c, rho=rho: c - rho * 0.5)
            ctx.part(finish(obj, 0.028, 0, 0), rigid(f"Lame{k}.{j}"))
            if j in (2, 3):
                seam = [fn(0.5, v) + nrm * 0.018 for v in lin(0.14, 0.80, 7)]
                ctx.part(trim(f"{T} lame seam {k}.{j}", seam, 0.010, M["inlay"]), rigid(f"Lame{k}.{j}"))
        tip = pts[-1]
        ctx.part(ellipsoid(f"{T} lame tip {k}", tip + rho * 0.035 - Vector((0, 0, 0.02)), (0.018, 0.018, 0.031), [M["glow"]], 8, 5),
                 rigid(f"Lame{k}.{LAME_J}"))
    # 导管线缆：甲片缝隙里的 8 条，连续蒙皮
    cables = []
    for i, g in enumerate(CABLE_GAPS):
        a, pts = cable_chain(i, g)
        cables.append((a, pts))
        dense, _ = catmull(pts, [1.0] * len(pts), per=10)
        acc, rads = 0.0, []
        for p_, nx in zip(dense, dense[1:] + [dense[-1]]):
            rads.append(0.032 + 0.007 * math.cos(acc / 0.055 * math.pi) ** 2)   # 分节导管的棱纹
            acc += (nx - p_).length
        bones = [f"Cable{i}.{j}" for j in range(1, 5)]
        ctx.part(tube(f"{T} cable {i}", dense, rads, [M["cable"]], n=8, per=1), chain(bones, "Pelvis", 0.10))
        for t, rr in ((0.06, 0.048), (0.985, 0.046)):
            f = t * (len(dense) - 1)
            q = min(len(dense) - 2, int(f))
            c = dense[q].lerp(dense[q + 1], f - q)
            dd = (dense[q + 1] - dense[q]).normalized()
            ctx.part(tube(f"{T} ferrule {i} {t}", [c - dd * 0.03, c + dd * 0.03], [rr, rr], [M["trim"]], n=14, per=1),
                     chain(bones, "Pelvis", 0.10))
        end = dense[-1]
        dd = (dense[-1] - dense[-2]).normalized()
        tx, tz = axis_frame(dd, (0, 1, 0))
        ctx.part(ellip(f"{T} cable tip {i}", end + dd * 0.05, (0.028, 0.06, 0.028), (tx, dd, tz), [M["glow"]], 10, 6),
                 rigid(bones[-1]))
    # 中央龙骨坠：三节象牙纺锤 + 金箍 + 发光晶坠
    for j in range(1, 5):
        a, b = KEEL[j - 1], KEEL[j]
        bone = f"Keel0.{j}"
        rm = (0.17, 0.14, 0.11, 0.09)[j - 1]
        L = (b - a).length
        if j < 4:
            prof = [(0.5 * rm, 0.0), (0.95 * rm, 0.25 * L), (rm, 0.45 * L), (0.75 * rm, 0.75 * L), (0.35 * rm, 0.98 * L)]
            sp = lathe_y(f"{ctx.title} keel {j}", prof, [M["ivory"]], seg=24, uv=lambda u, v: (u * 0.8, v * 0.6))
            place(sp, a, b - a, up=(0, 1, 0))
            ctx.part(sp, rigid(bone))
            for q in range(4):
                phi = q / 4 * TAU + TAU / 8
                rad = Vector((math.sin(phi), math.cos(phi), 0))
                pts = [a.lerp(b, t) + rad * (interp([(0.0, 0.5 * rm), (0.25, 0.95 * rm), (0.45, rm), (0.75, 0.75 * rm),
                                                     (0.98, 0.35 * rm)], t) + 0.006) for t in lin(0.22, 0.70, 6)]
                ctx.part(trim(f"{ctx.title} keel seam {j}{q}", pts, 0.008, M["inlay"]), rigid(bone))
        else:
            cage = lathe_y(f"{ctx.title} keel cap", [(0.05, 0.0), (0.09, 0.05), (0.08, 0.14), (0.05, 0.20)],
                           [M["gold"]], seg=20)
            place(cage, a, b - a, up=(0, 1, 0))
            ctx.part(cage, rigid(bone))
            dn = (b - a).normalized()
            cry = lathe_y(f"{ctx.title} keel crystal", [(0.0, 0.0), (0.075, 0.10), (0.06, 0.32), (0.0, L - 0.18)],
                          [M["glow"]], seg=8)
            place(cry, a + dn * 0.18, dn, up=(0, 1, 0))
            ctx.part(cry, rigid(bone))
            for q in range(4):
                phi = q / 4 * TAU
                rad = Vector((math.sin(phi), math.cos(phi), 0))
                ctx.part(spike(f"{ctx.title} keel prong {q}", a + dn * 0.16 + rad * 0.08, a + dn * 0.46 + rad * 0.02, 0.018,
                               [M["trim"]], sides=4, bend=0.03, up=rad), rigid(bone))
        ctx.part(trim(f"{ctx.title} keel collar {j}", circle(a, X, Y, 0.55 * rm + 0.03, 20), 0.018, M["trim"], closed=True),
                 rigid(bone))
    ctx.part(tube(f"{ctx.title} keel rod", KEEL[:4], [0.035] * 4, [M["dark"]], n=8, per=1),
             chain([f"Keel0.{j}" for j in range(1, 4)], "Pelvis", 0.05))
    return lames, cables


# ===== 构建入口 =====
def build(ctx):
    M = materials(ctx)
    ctx.marks["torso"] = build_torso(ctx, M)
    build_sun(ctx, M)
    build_back(ctx, M)
    build_head(ctx, M)
    muzzles = {}
    for n in (1, 2, 3):
        for side, label in SIDES:
            build_arm(ctx, M, n, side, label)
            if ARMS[n]["kind"] == "emitter":
                muzzles[(n, label)] = build_emitter(ctx, M, n, side, label)
            else:
                muzzles[(n, label)] = build_hand(ctx, M, side, label)
    build_halo(ctx, M)
    lames, cables = build_lower(ctx, M)
    stats(ctx, GAME_TRIS, LOD_KEEP)
    return {"lames": lames, "cables": cables, "muzzles": muzzles, "sun": ctx.marks["sun"],
            "beams": ctx.marks.get("beams", [])}


# ===== 骨骼 =====
def arm_bones():
    for n in (1, 2, 3):
        for side, label in SIDES:
            yield n, side, label


def skeleton(rig, st):
    rig.bone("Root", (0, 0, 0), (0, 0, 0.5))
    rig.bone("Hover", (0, 0, 0.5), (0, 0, 1.0), "Root")
    rig.translate["Hover"] = "_hover"
    rig.bone("Pelvis", (0, 0.02, 2.95), (0, 0.03, 3.40), "Hover", roll=Y)
    rig.bone("Spine", (0, 0.03, 3.40), (0, 0.05, 3.95), "Pelvis", roll=Y)
    rig.bone("Chest", (0, 0.05, 3.95), (0, 0.04, 4.62), "Spine", roll=Y)
    rig.bone("Neck", (0, 0.05, 4.62), (0, 0.10, 4.92), "Chest", roll=Y)
    rig.bone("Head", (0, 0.10, 4.92), (0, 0.12, 5.72), "Neck", roll=Y)
    sun = st["sun"]
    rig.bone("Sun", sun, sun + Vector((0, 0.3, 0)), "Chest", roll=Z)
    rig.bone("Mandorla", STRUT_BASE, HALO_C, "Chest", roll=X)
    for key, (off, _, _) in RINGS.items():
        c = HALO_C + HN * off
        rig.bone(f"Halo{key}", c, c - HN * 0.4, "Mandorla", roll=HV)
        rig.translate[f"Halo{key}"] = f"_h{key}"
    scaled = ["Sun", "HaloA", "HaloB", "HaloC"]
    for n, side, label in arm_bones():
        S, E, W = arm_pts(n, side)
        pole = rest_pole(n, side)
        rig.bone(f"Arm{n}.{label}", S, E, "Chest" if n < 3 else "Spine", roll=pole)
        rig.bone(f"Fore{n}.{label}", E, W, f"Arm{n}.{label}", roll=pole)
        m = st["muzzles"][(n, label)]
        if ARMS[n]["kind"] == "emitter":
            d = emit_dir(n, side)
            rig.bone(f"Hand{n}.{label}", W, W + d * EMIT_LEN * ARMS[n]["size"], f"Fore{n}.{label}", roll=pole)
        else:
            W, pn, fd, sd = hand_frame(side)
            rig.bone(f"Hand2.{label}", W, W + fd * 0.37, f"Fore2.{label}", roll=pn)
            for name, base, mid, tip, ax in finger_rest(side):
                rig.bone(f"{name}a.{label}", base, mid, f"Hand2.{label}", roll=pn)
                rig.bone(f"{name}b.{label}", mid, tip, f"{name}a.{label}", roll=pn)
            d = pn
        # Muzzle / Beam 同级挂在手骨上（避免光球缩放传给光束）；Beam 骨 Y 轴沿光束，缩放 Y 即伸缩长度
        rig.bone(f"Muzzle{n}.{label}", m, m + d * 0.25, f"Hand{n}.{label}")
        rig.bone(f"Beam{n}.{label}", m, m + d * 0.5, f"Hand{n}.{label}")
        scaled += [f"Muzzle{n}.{label}", f"Beam{n}.{label}"]
    for k, (a, pts) in enumerate(st["lames"]):
        rig.chain(f"Lame{k}.", pts, "Pelvis")
    for i, (a, pts) in enumerate(st["cables"]):
        rig.chain(f"Cable{i}.", pts, "Pelvis")
    rig.chain("Keel0.", KEEL, "Pelvis")
    rig.garments += [ChainSet("Lame", LAME_K, LAME_J), ChainSet("Cable", len(CABLE_GAPS), 4), ChainSet("Keel", 1, 4)]
    rig.scaled = scaled
    for beam in st["beams"]:
        beam.hide_render = False


# ===== 动作 =====
ARM_PH = {1: 0.0, 2: 2.1, 3: 4.2}
BEAM_FIRE = {3: 11.5, 2: 12.2, 1: 12.8}       # Attack 里三对发射器依次开火的帧（14 帧时六束全开）


def arm_axes(n, side):
    S, E, W = arm_pts(n, side)
    d1, d2 = (E - S).normalized(), (W - E).normalized()
    return raise_axis(d1), hinge(d1, d2), raise_axis(d2)


def set_fingers(p, curl, spread=0.0):
    """手指：curl 向掌心弯（两节），spread 以中指为界向两侧张开（拇指随食指一侧外展）。"""
    for side, label in SIDES:
        W, pn, fd, sd = hand_frame(side)
        sp_axis = fd.cross(sd).normalized()          # 绕它正转：手指偏向拇指一侧
        for i, (name, base, mid, tip, ax) in enumerate(finger_rest(side)):
            sp = spread * (0.8, 1.0, 0.0, -1.0)[i]
            c = curl * (0.7 if name == "F0" else 1.0)
            p[f"{name}a.{label}"] = R((ax, c * 0.55), (sp_axis, sp))
            p[f"{name}b.{label}"] = R((ax, c))


def set_rings(p, angles, dist=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
    for key, a, d, s in zip("ABC", angles, dist, scale):
        p[f"Halo{key}"] = R((HN, a))
        p[f"_h{key}"] = HN * d
        p["_scale"][f"Halo{key}"] = s


def set_glow(p, f, muzzle, sun, beams=(0.0, 0.0, 0.0)):
    sc = p["_scale"]
    sc["Sun"] = sun
    for n, side, label in arm_bones():
        sc[f"Muzzle{n}.{label}"] = muzzle
        b = beams[n - 1]
        bw = max(0.001, min(1.0, b * 2.5)) * (1 + 0.10 * math.sin(f * 1.9 + n) * min(1.0, b * 4))
        sc[f"Beam{n}.{label}"] = (bw, max(0.001, b), bw)


def set_chains(p, st, t, amp=1.0, back=0.0, flare=0.0, ripple=0.0):
    """垂挂件：flare 径向外掀、back 向后拖曳（统一绕 X）、sway 切向轻摆；按链深度累加。"""
    for group, K, amp_s, gain in (("Lame", st["lames"], 0.018, 1.0), ("Cable", st["cables"], 0.030, 1.0)):
        for k, (a, pts) in enumerate(K):
            tang = Vector((math.cos(a), -math.sin(a), 0))
            rad = Vector((math.sin(a), math.cos(a), 0))
            for j in range(1, 5):
                dep = depth_w(j, 4)
                fl = flare + 0.022 * amp * math.sin(t + k * 0.63 + j * 0.4) if group == "Lame" else flare * 0.6
                sw = amp_s * amp * math.sin(t + k * 0.9 + j * 0.5 + (0.8 if group == "Cable" else 0.0))
                bk = back * gain * (1 + ripple * math.sin(2 * t - k * 0.7 - j * 0.8))
                p[f"{group}{k}.{j}"] = R((X, -bk * dep)) @ R((tang, fl * dep)) @ R((rad, sw * dep))
    for j in range(1, 5):
        dep = depth_w(j, 4)
        p[f"Keel0.{j}"] = R((X, -back * 0.9 * dep + 0.012 * amp * math.sin(t + j * 0.6) * dep),
                            (Y, 0.015 * amp * math.sin(t + 1.7 + j * 0.5) * dep))


def idle_pose(rig, st, t, amp=1.0):
    p = {"_scale": {}}
    p["_hover"] = Vector((0, 0, 0.07 * amp * math.sin(t)))
    p["Pelvis"] = R((X, 0.012 * amp * math.sin(t + 0.4)))
    p["Spine"] = R((X, -0.010 * amp * math.sin(t + 0.9)))
    p["Chest"] = R((X, 0.018 * amp * math.sin(t + 1.3)), (Y, 0.008 * amp * math.sin(t)))
    p["Neck"] = R((X, -0.012 * amp * math.sin(t + 1.8)))
    p["Head"] = R((X, 0.02 * amp * math.sin(t + 2.1)), (Z, 0.035 * amp * math.sin(t + 0.5)))
    for n, side, label in arm_bones():
        ph = ARM_PH[n] + (0.0 if side > 0 else 0.9)
        ra, hx, rb = arm_axes(n, side)
        p[f"Arm{n}.{label}"] = R((ra, 0.05 * amp * math.sin(t + ph)), (Z, -side * 0.035 * amp * math.sin(t + ph + 1.1)))
        p[f"Fore{n}.{label}"] = R((hx, 0.07 * amp * math.sin(t + ph + 0.7)))
        p[f"Hand{n}.{label}"] = R((rb, 0.08 * amp * math.sin(t + ph + 1.4)))
    set_fingers(p, 0.12 + 0.06 * amp * math.sin(t + 1.3))
    p["Mandorla"] = R((X, 0.012 * amp * math.sin(t + 0.3)))
    set_rings(p, (t / 6, -t / 12, t / 12))          # 一循环：A 转 60°、B/C 各 30°（12 重对称的整数步进）
    set_chains(p, st, t, amp)
    set_glow(p, 0, 0.6 + 0.06 * amp * math.sin(2 * t), 1.0 + 0.05 * amp * math.sin(2 * t))
    return p


def move_pose(rig, st, t):
    p = idle_pose(rig, st, t, amp=0.5)
    p["_hover"] = Vector((0, 0, 0.10 + 0.05 * math.sin(t)))
    post(p, "Pelvis", R((X, -0.07 - 0.012 * math.sin(t))))
    post(p, "Spine", R((X, -0.05)))
    post(p, "Chest", R((X, -0.03 + 0.015 * math.sin(t + 0.8)), (Y, 0.02 * math.sin(t))))
    post(p, "Neck", R((X, 0.07)))
    post(p, "Head", R((X, 0.06 + 0.015 * math.sin(t + 1.5))))
    for n, side, label in arm_bones():
        sw = (0.28, 0.36, 0.30)[n - 1] + 0.04 * math.sin(t + ARM_PH[n] + (0.0 if side > 0 else 0.9))
        ra, hx, rb = arm_axes(n, side)
        post(p, f"Arm{n}.{label}", R((Z, -side * sw), (ra, (0.06, -0.05, 0.04)[n - 1])))
        post(p, f"Fore{n}.{label}", R((Z, -side * sw * 0.45)))
        post(p, f"Hand{n}.{label}", R((Z, -side * sw * 0.25)))
    set_fingers(p, 0.30 + 0.04 * math.sin(t + 1.3))
    post(p, "Mandorla", R((X, 0.06 + 0.01 * math.sin(t + 0.5))))
    set_rings(p, (t / 12, -t / 12, t / 12))         # 一循环各转 30°
    set_chains(p, st, t, amp=0.6, back=0.28, flare=0.02, ripple=0.14)
    return p


def action_pose(rig, st, q, f, F, spins):
    """一次性动作：以待机相位 2π(f-1)/F 为底（首尾帧与 Idle 首帧一致），叠加参数 q 的躯干 / IK 手臂 / 光环 / 发光。"""
    ph = TAU * (f - 1) / F
    s = (f - 1) / F
    p = idle_pose(rig, st, ph, amp=q["amp"])
    post(p, "Pelvis", R((X, -q["lean"] * 0.45)))
    post(p, "Spine", R((X, -q["lean"] * 0.30 + q["arch"] * 0.4)))
    post(p, "Chest", R((X, -q["lean"] * 0.25 + q["arch"] * 0.6), (Z, q["shake"] * 0.3)))
    post(p, "Neck", R((X, q["head"] * 0.4)))
    post(p, "Head", R((X, q["head"] * 0.6), (Z, q["shake"])))
    p["_hover"] = p["_hover"] + Vector((0, 0, q["rise"]))
    post(p, "Mandorla", R((X, q["tilt"])))
    w = q["ik"]
    if w > 1e-4:
        pk = dict(p)
        for n, side, label in arm_bones():
            tgt = mirror(q[f"w{n}"], side) + Vector((0, 0, q["tremor"] * math.sin(f * 2.7 + n * 1.3 + side)))
            rig.ik2(pk, f"Arm{n}.{label}", f"Fore{n}.{label}", tgt, mirror(q[f"pole{n}"], side).normalized(),
                    rest_pole=rest_pole(n, side))
            aim = mirror(q[f"aim{n}"], side)
            wrist = rig.tail(pk, f"Fore{n}.{label}")
            if ARMS[n]["kind"] == "emitter":
                rig.aim(pk, f"Hand{n}.{label}", aim - wrist)
            else:
                W, pn, fd, sd = hand_frame(side)
                pdir = (aim - wrist).normalized()
                up = Vector((side * 0.35, 0, 1.0))
                up = (up - pdir * up.dot(pdir)).normalized()
                rig.aim(pk, f"Hand2.{label}", up, up=pdir, rest_up=pn)
        for n, side, label in arm_bones():
            for b in (f"Arm{n}.{label}", f"Fore{n}.{label}", f"Hand{n}.{label}"):
                p[b] = slerp_m(p.get(b), pk.get(b), w)
    set_fingers(p, 0.12 + 0.06 * q["amp"] * math.sin(ph + 1.3) + q["curl"], q["spread"])
    set_rings(p, tuple(spins[k](s) for k in "ABC"), (q["dA"], q["dB"], q["dC"]), (q["sA"], q["sB"], q["sC"]))
    set_chains(p, st, ph, q["amp"], back=q["back"], flare=q["flare"])
    beams = tuple(q.get(f"beam{n}", 0.0) for n in (1, 2, 3))
    set_glow(p, f, 0.6 + 0.06 * q["amp"] * math.sin(2 * ph) + q["muzzle"],
             1.0 + 0.05 * q["amp"] * math.sin(2 * ph) + q["sun"], beams)
    return p


def base_params():
    q = {"amp": 1.0, "lean": 0.0, "arch": 0.0, "head": 0.0, "shake": 0.0, "rise": 0.0, "tilt": 0.0, "ik": 0.0,
         "curl": 0.0, "spread": 0.0, "muzzle": 0.0, "sun": 0.0, "dA": 0.0, "dB": 0.0, "dC": 0.0,
         "sA": 1.0, "sB": 1.0, "sC": 1.0, "back": 0.0, "flare": 0.0, "tremor": 0.0}
    for n in (1, 2, 3):
        S, E, W = arm_pts(n, 1)
        q[f"w{n}"] = W.copy()
        q[f"pole{n}"] = rest_pole(n, 1)
        d = emit_dir(n, 1) if ARMS[n]["kind"] == "emitter" else hand_frame(1)[1]
        q[f"aim{n}"] = W + d * 3.0
    return q


def attack_keys():
    """光束齐射：1 → 6 收臂蓄能 → 11 六臂前指瞄准 → 12–14 依次开火（交叉光束）→ 14–22 持续照射 → 26 收束 → 33 复位。"""
    base = base_params()
    aims = {"aim1": Vector((-1.1, 5.2, 3.0)), "aim2": Vector((-1.2, 5.0, 3.5)), "aim3": Vector((-1.0, 4.8, 3.7))}
    poles = {"pole1": Vector((1, -0.3, -0.3)), "pole2": Vector((0.5, -0.4, -0.8)), "pole3": Vector((1, -0.2, -0.6))}
    draw = {"ik": 1.0, "arch": 0.06, "lean": -0.04, "head": 0.04, "amp": 0.5, "tilt": -0.04,
            "w1": Vector((1.80, -0.30, 5.45)), "w2": Vector((2.15, -0.20, 4.20)), "w3": Vector((1.40, 0.10, 3.25)),
            "muzzle": 0.30, "sun": 0.15, "curl": -0.15, "spread": 0.10, "flare": 0.04, **aims, **poles}
    aim = dict(draw, lean=0.10, arch=0.0, head=-0.05, amp=0.3, muzzle=0.55, sun=0.30, flare=0.03,
               w1=Vector((1.55, 0.85, 5.35)), w2=Vector((1.95, 1.20, 4.05)), w3=Vector((1.25, 1.35, 3.05)))
    fire = dict(aim, lean=0.03, arch=0.05, muzzle=0.75, sun=0.40, dA=0.06, sA=1.03, tremor=0.012, flare=0.06)
    hold = dict(fire, lean=0.07, arch=0.02, muzzle=0.60, sun=0.35, tremor=0.010, flare=0.05)
    sweep_end = dict(hold, aim1=Vector((-0.5, 5.2, 3.1)), aim2=Vector((-0.6, 5.0, 3.5)), aim3=Vector((-0.4, 4.8, 3.6)))
    relax = dict(base, ik=0.55, lean=0.02, amp=0.6, muzzle=0.2, sun=0.2, **aims, **poles,
                 w1=Vector((1.85, 0.30, 5.60)), w2=Vector((2.30, 0.70, 3.95)), w3=Vector((1.45, 1.05, 2.95)))
    return with_defaults(base, [(1, {}, "io"), (6, draw, "io"), (11, aim, "io"), (14, fire, "out"), (17, hold, "io"),
                                (22, sweep_end, "lin"), (26, relax, "io"), (33, {}, "io")])


def enrage_keys():
    """狂暴：1 → 10 收拢蓄势（光环收紧、日核内敛）→ 17 爆发：六臂全开、光环加速分离外扩 → 24–34 持续震颤 →
    42 回落 → 49 复位。"""
    base = base_params()
    gather = {"ik": 1.0, "lean": 0.18, "head": -0.20, "arch": -0.04, "amp": 0.3, "rise": -0.04, "tilt": 0.05,
              "w1": Vector((1.10, 0.75, 4.95)), "w2": Vector((1.45, 1.00, 3.95)), "w3": Vector((1.00, 1.00, 3.12)),
              "aim1": Vector((-0.3, 2.2, 4.1)), "aim2": Vector((-0.3, 2.4, 4.0)), "aim3": Vector((-0.3, 2.2, 3.8)),
              "pole1": Vector((1, -0.5, -0.6)), "pole2": Vector((1, -0.3, -0.8)), "pole3": Vector((1, -0.3, -0.5)),
              "curl": 0.95, "spread": -0.05, "muzzle": -0.25, "sun": -0.25, "sA": 0.94, "sB": 0.94, "sC": 0.94,
              "flare": -0.03}
    burst = {"ik": 1.0, "lean": -0.16, "arch": 0.14, "head": 0.40, "amp": 0.15, "rise": 0.20, "tilt": -0.08,
             "w1": Vector((2.00, -0.15, 6.05)), "w2": Vector((2.66, 0.05, 4.40)), "w3": Vector((1.95, 0.30, 2.55)),
             "aim1": Vector((3.2, -0.15, 9.0)), "aim2": Vector((4.5, 2.8, 4.8)), "aim3": Vector((4.2, 1.8, 0.8)),
             "pole1": Vector((0.3, -1, 0)), "pole2": Vector((0, -1, -0.6)), "pole3": Vector((0.3, -1, 0.3)),
             "curl": -0.15, "spread": 0.25, "muzzle": 0.70, "sun": 0.50, "dA": 0.18, "dB": -0.30, "dC": -0.80,
             "sA": 1.10, "sB": 1.22, "sC": 1.38, "flare": 0.22, "tremor": 0.02}
    roar = dict(burst, head=0.44, arch=0.16, flare=0.18, muzzle=0.80, sun=0.55, rise=0.22, shake=0.0)
    roar2 = dict(roar, flare=0.17)
    settle = dict(base, ik=0.5, lean=0.02, arch=0.02, head=0.05, amp=0.7, muzzle=0.2, sun=0.2, dA=0.03, dB=-0.05,
                  dC=-0.10, sA=1.02, sB=1.02, sC=1.03, flare=0.03, rise=0.03,
                  w1=Vector((1.95, -0.05, 5.95)), w2=Vector((2.55, 0.35, 4.05)), w3=Vector((1.70, 0.70, 2.75)),
                  pole1=burst["pole1"], pole2=burst["pole2"], pole3=burst["pole3"])
    return with_defaults(base, [(1, {}, "io"), (10, gather, "io"), (17, burst, "out"), (24, roar, "io"),
                                (34, roar2, "lin"), (42, settle, "io"), (49, {}, "io")])


def bump(s, c, w):
    return math.exp(-((s - c) / w) ** 2)


def animate(rig, st):
    loop(rig, "Idle", 120, lambda t: idle_pose(rig, st, t), step=2)
    loop(rig, "Move", 48, lambda t: move_pose(rig, st, t), step=1)
    ak = attack_keys()
    a_spins = {"A": spin_curve(lambda s: 0.15 + bump(s, 0.45, 0.22), TAU),
               "B": spin_curve(lambda s: 0.15 + bump(s, 0.50, 0.25), -TAU),
               "C": lambda s: 0.10 * math.sin(math.pi * s) ** 2}

    def attack(f):
        q = track(ak, f)
        for n in (1, 2, 3):
            q[f"beam{n}"] = smoothstep(BEAM_FIRE[n], BEAM_FIRE[n] + 1.5, f) * (1 - smoothstep(22, 25, f))
        return action_pose(rig, st, q, f, 32, a_spins)
    sampled(rig, "Attack", 32, attack)
    ek = enrage_keys()
    e_spins = {"A": spin_curve(lambda s: 0.12 + 1.6 * bump(s, 0.52, 0.22), 2 * TAU),
               "B": spin_curve(lambda s: 0.12 + 1.6 * bump(s, 0.55, 0.24), -2 * TAU),
               "C": spin_curve(lambda s: 0.12 + 1.6 * bump(s, 0.50, 0.20), TAU)}

    def enrage(f):
        q = track(ek, f)
        if 17 <= f <= 38:
            k = smoothstep(17, 20, f) * (1 - smoothstep(34, 38, f))
            q["shake"] += 0.03 * math.sin(f * 2.3) * k
        return action_pose(rig, st, q, f, 48, e_spins)
    sampled(rig, "Enrage", 48, enrage)
    seam_check(rig, ("Idle", "Move"), {f"Halo{k}": 30.0 for k in "ABC"})
    tips = [("Keel0.4", 0.0)] + [(f"Cable{i}.4", -0.07) for i in range(len(CABLE_GAPS))] + \
        [(f"Lame{k}.4", 0.0) for k in range(LAME_K)]
    clearance(rig, CLIPS, tips)
