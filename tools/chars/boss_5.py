"""零域先知 · 腐化祭坛（The Null Oracle · Corrupted Altar）· Boss 5。

设定：祭坛与先知合体，总高约 6.5 m。下部是悬浮的黑石八棱祭坛（龙骨晶簇、底座、刻符鼓座、黑玻璃祭台面、
正面“虚空井”独眼徽记），脚下地面有旋转的符文井环；祭台上升起兜帽先知：尖顶兜帽的上半冠分成左右两瓣
（狂暴时裂开，露出头顶的眼冠），骨瓷面具、兜帽、披肩、长袍、光环、掌心、虚空球上布满发光的眼睛；
长袍从腰间铺满祭台并垂过台沿。六块方尖碑碎片与三颗虚空眼球同环公转（骨骼驱动），脚边一圈晶屑反向公转。
动作：Idle（悬浮、慢速公转）/ Move（前倾滑行）/ Attack（举臂 → 张臂开井，虚空球外扩脉动、井环扩张）/
Enrage（碎片加速公转，兜帽冠瓣裂开、眼冠升起）。
公转无缝：碎片按两种形制交替（三重对称），每个循环公转 120°，浮动相位取“当前槽位角 + 时间”，
所以循环首尾在视觉上完全一致；一次性动作结束时的转角都是对称角的整数倍。
"""

import math

import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import bpy
from kit.core import (TAU, apply_all, auto_smooth, bands, bm_object, boundary_loops, circuit_maps, crack_maps, crest,
                      ellipsoid, filigree_maps, finish, fn, garment, hash01, interp, invdist, lerp, loft, orient,
                      plate, radial, rigid, rune_maps, smoothstep, solidify, spike, subsurf, surface, transform, trim,
                      tube)
from kit.garment import Panel, Wrap, tail_weight
from kit.rig import R, X, Y, Z
from chars._b5_kit import (KEEP, Track, ease, eye, flat_ring, key_scale, mix, oct_points, oriented_ellipsoid, prism,
                           spin_curve, sq, stats, surf_frame, sweep)
from chars._b5_kit import gem_lo as gem

TITLE = "Null Oracle"
ACCENT = (0.89, 0.61, 0.95)
CLIPS = ("Idle", "Move", "Attack", "Enrage")
GAME_TRIS = 85000
LOD_KEEP = KEEP
REVIEW_POSE = ("Idle", 1)
EYE = (1.0, 0.36, 0.90)
SIDES = ((-1, "L"), (1, "R"))

# 兜帽：顶点高度、下缘高度、冠瓣分割线高度（分割线以上左右两瓣可裂开）
HOOD_TOP, HOOD_BOT, HOOD_SPLIT = 5.64, 4.34, 4.90
VS = (HOOD_TOP - HOOD_SPLIT) / (HOOD_TOP - HOOD_BOT)
CREST_C = Vector((0.0, -0.10, 4.96))
MASK_C = Vector((0.0, 0.13, 4.74))
HALO_C = Vector((0.0, -0.80, 5.02))
HALO_R = 1.02
# 公转环：六块方尖碑碎片（两型交替）+ 三颗虚空眼球（位于碎片间隙），同一根公转骨
RING_R, ORB_R, ORB_Z, ORB_RAD = 2.45, 2.15, 4.25, 0.28
N_SH, N_ORB, N_CHIP = 6, 3, 12
SH_PHASE = math.pi / 6          # 碎片槽位 30°+60°k，正前方留空不挡脸；虚空球在 60°+120°k 的间隙
HS = 1.3                        # 手掌放大（Boss 体量下爪手要读得出来）
SHARD_T = ({"L": 1.55, "hw": (0.17, 0.13), "z0": 3.10, "tip": 0.34, "seed": 7.3},
           {"L": 1.10, "hw": (0.15, 0.115), "z0": 2.38, "tip": 0.28, "seed": 4.1})


def rd(a):
    return Vector((math.sin(a), math.cos(a), 0.0))


def td(a):
    return Vector((math.cos(a), -math.sin(a), 0.0))


def lancet(w, h, n=8):
    """哥特尖拱轮廓（x 横向，y 向上），底宽 w、高 h。"""
    pts = [(-w / 2, 0.0)]
    for i in range(1, n + 1):
        t = i / n
        pts.append((-w / 2 * (1 - t ** 1.6) * (1 - 0.15 * math.sin(math.pi * t)), h * (t ** 0.85) if i < n else h))
    for i in range(n - 1, 0, -1):
        t = i / n
        pts.append((w / 2 * (1 - t ** 1.6) * (1 - 0.15 * math.sin(math.pi * t)), h * (t ** 0.85)))
    pts.append((w / 2, 0.0))
    return pts


def materials(ctx):
    M = ctx.M
    ctx.mat("stone", "corrupted basalt", (0.022, 0.019, 0.026), metal=0.15, rough=0.55, coat=0.25)
    ctx.texture("stone", crack_maps(tuple(c * 0.85 for c in ACCENT), base_rgb=(0.032, 0.027, 0.038), size=1024,
                                    seed=51, cells=7, width=0.032, heat=0.55), emit_strength=1.8, normal_strength=0.5)
    ctx.mat("rune", "void rune band", (0.03, 0.025, 0.035), metal=0.3, rough=0.4, coat=0.4)
    ctx.texture("rune", rune_maps(ACCENT, base_rgb=(0.020, 0.017, 0.026), size=1024, seed=55, rows=4, cols=8),
                emit_strength=3.4, normal_strength=0.5)
    ctx.mat("glass", "black void glass", (0.006, 0.005, 0.009), metal=0.1, rough=0.06, coat=1.0, spec=0.8)
    ctx.mat("gilt", "antique gilt", (0.80, 0.62, 0.38), metal=1.0, rough=0.30)
    ctx.texture("gilt", filigree_maps((0.78, 0.60, 0.36), (0.40, 0.27, 0.14), size=1024, seed=57, density=22,
                                      width=1), normal_strength=0.35)
    ctx.mat("trim", "gilt trim", (0.84, 0.66, 0.40), metal=1.0, rough=0.26)
    ctx.mat("gold", "burnished gold", (0.82, 0.63, 0.38), metal=1.0, rough=0.24)
    ctx.mat("robe", "void velvet robe", (0.016, 0.010, 0.022), rough=0.8, sheen=0.1, sheen_tint=(0.7, 0.45, 0.8),
            spec=0.3)
    ctx.texture("robe", circuit_maps(ACCENT, base_rgb=(0.014, 0.009, 0.020), size=2048, seed=59, buses=16),
                emit_strength=2.6)
    ctx.mat("lining", "orchid satin lining", (0.10, 0.025, 0.12), rough=0.48, sheen=0.12, sheen_tint=(0.8, 0.35, 0.9),
            spec=0.35)
    ctx.mat("void", "hood void", (0.003, 0.002, 0.005), rough=0.95, emit=(0.40, 0.18, 0.55), strength=0.06)
    ctx.mat("mask", "bone porcelain mask", (0.74, 0.70, 0.66), rough=0.32, coat=0.6, spec=0.5)
    ctx.mat("glow", "oracle core glow", (0.6, 0.4, 0.7), emit=ACCENT, strength=6.0)
    ctx.mat("inlay", "oracle rune inlay", (0.35, 0.22, 0.4), emit=ACCENT, strength=3.4)
    ctx.mat("hem", "void hem light", (0.3, 0.18, 0.35), emit=ACCENT, strength=4.5)
    ctx.mat("eye", "oracle eye glow", (0.45, 0.12, 0.40), emit=EYE, strength=3.2)
    ctx.mat("pupil", "oracle eye pupil", (0.004, 0.002, 0.006), metal=0.2, rough=0.1, coat=1.0)
    return M


# ===== 祭坛（挂 Altar 骨） =====
def octrim(ctx, M, name, r, z, rad, spec, mat="trim"):
    ctx.part(trim(name, oct_points(r, z), rad, M[mat], closed=True, n=6, per=1), spec)


def box_post(name, c, n, hw, z0, z1, mats):
    """贴在棱角上的方柱（带 UV）：c 为水平中心、n 为朝外方向。"""
    t = Vector((n.y, -n.x, 0))
    secs = []
    for z in (z1, z0):
        secs.append([c + n * (hw * sx) + t * (hw * sy) + Vector((0, 0, z))
                     for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    return auto_smooth(loft(name, secs, mats, closed_u=True, cap=True), 30)


def build_altar(ctx, M):
    T, sp = ctx.title, rigid("Altar")
    ctx.part(prism(f"{T} keel", [(0.46, 0.14), (1.16, 0.26), (1.54, 0.36)], [M["stone"]], bev=0.02), sp)
    ctx.part(prism(f"{T} plinth", [(1.62, 0.36), (1.62, 0.70), (1.55, 0.76)], [M["stone"]], bev=0.025), sp)
    ctx.part(prism(f"{T} drum", [(1.30, 0.76), (1.27, 1.44)], [M["stone"]], bev=0.02), sp)
    ctx.part(prism(f"{T} mensa", [(1.29, 1.44), (1.40, 1.52), (1.40, 1.74), (1.34, 1.80)], [M["stone"], M["glass"]],
                   cap_mats=(0, 1), bev=0.015), sp)
    for name, r, z, rad in (("keel rim", 0.47, 0.145, 0.014), ("plinth foot", 1.635, 0.375, 0.02),
                            ("plinth lip", 1.60, 0.728, 0.022), ("drum foot", 1.31, 0.79, 0.02),
                            ("drum lip", 1.285, 1.425, 0.018), ("mensa lip", 1.415, 1.52, 0.022),
                            ("mensa edge", 1.375, 1.775, 0.02)):
        octrim(ctx, M, f"{T} {name}", r, z, rad, sp)
    # 鼓座七面符文板（正面留给虚空井徽记）
    fd = 1.285 * math.cos(math.pi / 8)
    for k in range(1, 8):
        a = k * TAU / 8
        n, t = rd(a), td(a)
        u0, v0 = hash01(k, 3.1), 0.5 * (k % 2)

        def pp(u, v, n=n, t=t):
            return n * (fd + 0.012) + t * ((u - 0.5) * 0.60) + Vector((0, 0, lerp(1.32, 0.88, v)))
        pan = surface(f"{T} rune panel {k}", pp, 2, 2, [M["rune"]],
                      uvfn=lambda u, v, u0=u0, v0=v0: (u0 + u * 0.31, v0 + 0.5 * (1 - v)))
        orient(pan, lambda c, n=n: c - n)
        ctx.part(finish(pan, 0.022, -1, 0), sp)
        frame = [pp(u, v) + n * 0.006 for u, v in ((-0.03, -0.05), (1.03, -0.05), (1.03, 1.05), (-0.03, 1.05))]
        ctx.part(trim(f"{T} rune frame {k}", frame, 0.013, M["trim"], closed=True, per=1), sp)
    # 八根棱角壁柱：黑石柱身 + 金柱头柱础 + 竖向光缝
    for k in range(8):
        b = math.pi / 8 + k * TAU / 8
        n = rd(b)
        c = n * 1.265
        ctx.part(box_post(f"{T} pilaster {k}", c, n, 0.075, 0.80, 1.42, [M["stone"]]), sp)
        for z0, z1 in ((0.78, 0.86), (1.36, 1.44)):
            ctx.part(box_post(f"{T} pilaster cap {k} {z0}", c, n, 0.092, z0, z1, [M["gilt"]]), sp)
        ctx.part(trim(f"{T} pilaster slit {k}", [c + n * 0.079 + Vector((0, 0, z)) for z in (0.90, 1.34)], 0.011,
                      M["inlay"], n=4, per=1), sp)
    # 正面虚空井徽记：黑玻璃尖拱 + 金框 + 巨眼 + 放射金芒
    fc = Vector((0, fd + 0.012, 0))
    arch = lancet(0.64, 0.58, n=10)
    ctx.part(plate(f"{T} frontal", arch, 0.03, [M["glass"]], origin=fc + Vector((0, 0, 0.82)), xaxis=(1, 0, 0),
                   yaxis=(0, 0, 1), bev=0.004), sp)
    ctx.part(trim(f"{T} frontal frame", [fc + Vector((x, 0.018, 0.82 + y)) for x, y in arch], 0.014, M["trim"],
                  closed=True, per=1), sp)
    ec = Vector((0, fd + 0.03, 1.06))
    eye(ctx, M, f"{T} frontal eye", ec, (0, 1, 0), (0, 0, 1), 0.18, 0.072, sp, lash=0.07, rim=0.012)
    for i in range(7):
        ang = lerp(-1.0, 1.0, i / 6)
        d = Vector((math.sin(ang), 0, math.cos(ang)))
        base = ec + Vector((d.x * 0.20, 0, d.z * 0.10))
        L = 0.15 if i % 2 == 0 else 0.09
        ctx.part(spike(f"{T} frontal ray {i}", base, base + d * L, 0.012, [M["trim"]], sides=4, up=(0, 1, 0)), sp)
    ctx.part(gem(f"{T} frontal tear", ec + Vector((0, 0.006, -0.15)), 0.022, M["glow"], (0.6, 0.5, 1.5)), sp)
    # 祭台面：光圈 + 金圈 + 长袍脚下的虚空池
    for r, rad, mat in ((1.17, 0.012, "glow"), (1.25, 0.016, "trim"), (0.84, 0.020, "glow"), (0.90, 0.016, "trim")):
        ring = [Vector((math.sin(a) * r, math.cos(a) * r, 1.806)) for a in [i / 72 * TAU for i in range(72)]]
        ctx.part(trim(f"{T} mensa ring {r}", ring, rad, M[mat], closed=True, n=4, per=1), sp)
    # 底座八面单行符文带 + 八角金爪饰与角灯
    pd = 1.62 * math.cos(math.pi / 8)
    for k in range(8):
        a = k * TAU / 8
        n, t = rd(a), td(a)

        def bp(u, v, n=n, t=t):
            return n * (pd + 0.008) + t * ((u - 0.5) * 1.02) + Vector((0, 0, lerp(0.62, 0.46, v)))
        strip = surface(f"{T} plinth runes {k}", bp, 2, 2, [M["rune"]],
                        uvfn=lambda u, v, k=k: (hash01(k, 8.3) + u * 0.80, 0.25 * (1 - v)))
        orient(strip, lambda c, n=n: c - n)
        ctx.part(finish(strip, 0.016, -1, 0), sp)
        b = math.pi / 8 + a
        nb = rd(b)
        corner = nb * 1.60 + Vector((0, 0, 0.74))
        ctx.part(spike(f"{T} plinth claw {k}", corner, corner + nb * 0.26 + Vector((0, 0, 0.16)), 0.06, [M["gold"]],
                       sides=4, up=(0, 0, 1), bend=0.05), sp)
        ctx.part(gem(f"{T} plinth lamp {k}", nb * 1.66 + Vector((0, 0, 0.55)), 0.034, M["glow"], (1, 1, 1.3)), sp)
    # 龙骨下方的倒悬晶簇与虚空之眼
    for k in range(8):
        n = rd(k * TAU / 8)
        base = n * 0.95 + Vector((0, 0, 0.25))
        ctx.part(spike(f"{T} keel crystal {k}", base, n * 1.30 + Vector((0, 0, 0.12)), 0.075, [M["glass"]], sides=5), sp)
        ctx.part(gem(f"{T} keel crystal gem {k}", base + n * 0.03, 0.03, M["glow"], (1, 1, 1)), sp)
    ctx.part(ellipsoid(f"{T} keel core", (0, 0, 0.14), (0.22, 0.22, 0.05), [M["glow"]], 24, 8), sp)


def build_well(ctx, M):
    """地面虚空井环（挂 Well 骨，Attack 时扩张）。"""
    T, sp = ctx.title, rigid("Well")
    ctx.part(flat_ring(f"{T} well runes", (0, 0, 0.014), 1.95, 2.20, [M["rune"]], seg=144, thick=0.008,
                       uvfn=lambda u, v: (u * 6, 0.75 + 0.25 * v)), sp)
    for r, rad in ((1.88, 0.010), (2.28, 0.012)):
        ring = [Vector((math.sin(a) * r, math.cos(a) * r, 0.016)) for a in [i / 96 * TAU for i in range(96)]]
        ctx.part(trim(f"{T} well line {r}", ring, rad, M["inlay"], closed=True, n=4, per=1), sp)
    for k in range(12):
        a = k * TAU / 12
        dia = [(0.0, 0.0), (0.09, 0.035), (0.20, 0.0), (0.09, -0.035)]
        ctx.part(plate(f"{T} well tick {k}", dia, 0.006, [M["inlay"]], origin=rd(a) * 2.33 + Vector((0, 0, 0.014)),
                       xaxis=tuple(rd(a)), yaxis=tuple(td(a))), sp)


def build_chips(ctx, M):
    """祭坛腰部反向公转的一圈晶屑（挂 OrbitC 骨，两型交替 → 六重对称）。"""
    T, sp = ctx.title, rigid("OrbitC")
    for k in range(N_CHIP):
        a = k * TAU / N_CHIP
        c = rd(a) * 1.98 + Vector((0, 0, 1.10 + 0.07 * (k % 2)))
        ch = ellipsoid(f"{T} chip {k}", (0, 0, 0), (0.045, 0.045, 0.10 + 0.03 * (k % 2)),
                       [M["glass"] if k % 2 == 0 else M["inlay"]], 4, 2)
        transform(ch, Matrix.Translation(c) @ Matrix.Rotation(0.35 if k % 2 else -0.35, 4, td(a)))
        ctx.part(auto_smooth(ch, 30), sp)


# ===== 方尖碑碎片（每块一根骨，挂 OrbitS） =====
def shard_slot(k):
    return SH_PHASE + k * TAU / N_SH


def shard_matrix(k):
    ty = SHARD_T[k % 2]
    a = shard_slot(k)
    pos = rd(a) * RING_R + Vector((0, 0, ty["z0"]))
    return Matrix.Translation(pos) @ Matrix.Rotation(-a, 4, "Z") @ Matrix.Rotation(-0.09, 4, "X")


def shard_axis(k):
    return (shard_matrix(k).to_3x3() @ Vector((0, 0, 1))).normalized()


def build_shard(ctx, M, k):
    T, ty = ctx.title, SHARD_T[k % 2]
    sp = rigid(f"Shard{k}")
    L, (hw0, hw1), tip = ty["L"], ty["hw"], ty["tip"]
    mtx = shard_matrix(k)
    rot = mtx.to_3x3()

    def hw_at(z):
        return lerp(hw0, hw1, z / L)
    # 同型碎片几何完全一致（种子只取决于型号），公转循环才能无缝
    jit = lambda i: -0.13 * hash01(i, ty["seed"]) + 0.03 * hash01(i + 9, ty["seed"])
    objs = []
    body = loft(f"{T} shard {k}", [sq(hw1, L), sq(hw_at(L * 0.5), L * 0.5), sq(hw0, 0.0, jit=jit)], [M["stone"]],
                closed_u=True, cap=True)
    objs.append(auto_smooth(body, 30))
    objs.append(auto_smooth(loft(f"{T} shard collar {k}", [sq(hw_at(L - 0.05) + 0.016, L - 0.05),
                                                            sq(hw_at(L - 0.16) + 0.018, L - 0.16)],
                                 [M["gilt"]], closed_u=True, cap=True), 30))
    objs.append(auto_smooth(loft(f"{T} shard cap {k}", [sq(0.006, L + tip), sq(hw1 + 0.008, L - 0.004, ch=0.12)],
                                 [M["gilt"]], closed_u=True, cap=True), 30))
    for f in range(4):
        nf = Vector((math.cos(f * math.pi / 2), math.sin(f * math.pi / 2), 0))
        lat = Vector((-nf.y, nf.x, 0))
        pts = []
        for j in range(6):
            z = lerp(0.16 * L, 0.80 * L, j / 5)
            pts.append(nf * (hw_at(z) + 0.004) + lat * (0.024 * (1 if j % 2 else -1) * (0.4 if j in (0, 5) else 1))
                       + Vector((0, 0, z)))
        objs.append(trim(f"{T} shard slit {k}{f}", pts, 0.010, M["inlay"], n=4, per=1))
    objs.append(ellipsoid(f"{T} shard fracture {k}", (0, 0, -0.03), (hw0 * 0.78, hw0 * 0.78, 0.05), [M["glow"]], 12, 6))
    for j, (x, y, z, s) in enumerate(((0.10, 0.05, -0.24, 0.05), (-0.08, -0.06, -0.40, 0.04), (0.03, 0.09, -0.55, 0.03))):
        chip = ellipsoid(f"{T} shard chip {k}{j}", (x, y, z * (L / 1.3)), (s, s, s * 1.8), [M["glass"]], 4, 2)
        objs.append(auto_smooth(chip, 30))
    for o in objs:
        transform(o, mtx)
        ctx.part(o, sp)
    if k % 2 == 0:
        c = mtx @ Vector((0, hw_at(0.70 * L) + 0.004, 0.70 * L))
        eye(ctx, M, f"{T} shard eye {k}", c, rot @ Vector((0, 1, 0)), rot @ Vector((0, 0, 1)), 0.075, 0.030, sp,
            lash=0.035)


# ===== 虚空眼球（每颗一根骨，挂 OrbitS） =====
def orb_center(k):
    a = SH_PHASE + math.pi / 6 + k * TAU / N_ORB
    return a, rd(a) * ORB_R + Vector((0, 0, ORB_Z))


def build_orb(ctx, M, k):
    T = ctx.title
    a, c = orb_center(k)
    sp = rigid(f"Orb{k}")
    n, t = rd(a), td(a)
    ctx.part(ellipsoid(f"{T} orb {k}", c, (ORB_RAD,) * 3, [M["glass"]], 28, 18), sp)
    # 眼窝光环：与眼睛方向垂直的大圆，把眼球分成“注视面”和背面
    belt = [c + t * (math.sin(q) * (ORB_RAD + 0.004)) + Vector((0, 0, math.cos(q) * (ORB_RAD + 0.004)))
            for q in [i / 48 * TAU for i in range(48)]]
    ctx.part(trim(f"{T} orb belt {k}", belt, 0.012, M["glow"], closed=True, n=4, per=1), sp)
    tilt = Matrix.Rotation(0.49, 3, t)
    ring = [c + tilt @ Vector((math.sin(q) * 0.40, math.cos(q) * 0.40, 0)) for q in [i / 48 * TAU for i in range(48)]]
    ctx.part(tube(f"{T} orb armillary {k}", ring, [0.016] * 48, [M["gold"]], n=5, closed=True, per=1), sp)
    for j in range(3):
        ctx.part(gem(f"{T} orb node {k}{j}", ring[j * 16 + 8], 0.030, M["glow"], (1, 1, 1)), sp)
    eye(ctx, M, f"{T} orb eye {k}", c + n * (ORB_RAD - 0.012), n, (0, 0, 1), 0.13, 0.072, sp, rim=0.012, pupil=0.18)


# ===== 先知躯干 =====
TORSO = [(2.86, (0.37, 0.31, 0.00)), (3.10, (0.39, 0.31, 0.01)), (3.40, (0.44, 0.33, 0.02)),
         (3.70, (0.50, 0.35, 0.02)), (3.95, (0.53, 0.34, 0.01)), (4.12, (0.47, 0.30, 0.0)),
         (4.26, (0.30, 0.22, 0.0)), (4.36, (0.18, 0.16, 0.01))]
TORSO_SPEC = bands([(4.20, "Chest"), (3.72, "Chest"), (3.32, "Spine"), (3.02, "Pelvis")])


def torso_pt(a, z, grow=0.0):
    rx, ry, yo = interp(TORSO, z)
    return Vector(((rx + grow) * math.sin(a), yo + (ry + grow) * math.cos(a), z))


def front_pt(x, z, grow):
    rx = interp(TORSO, z)[0] + grow
    return torso_pt(math.asin(max(-0.999, min(0.999, x / rx))), z, grow)


def plack_pt(u, v, extra=0.0):
    a = lerp(-0.95, 0.95, u)
    zt = 3.80 - 0.04 * (1 - math.cos(a))
    zb = 3.06 - 0.10 * max(0.0, math.cos(a)) ** 8
    g = 0.022 + 0.018 * math.sin(math.pi * v) * max(0.0, math.cos(a)) + extra
    return torso_pt(a, lerp(zt, zb, v), g)


def build_body(ctx, M):
    T = ctx.title
    body = surface(f"{T} torso", lambda u, v: torso_pt(u * TAU, lerp(4.36, 2.86, v)), 40, 26, [M["robe"]],
                   closed_u=True, uvfn=lambda u, v: (u * 2, 0.5 * v))
    orient(body, lambda c: Vector((0, 0.01, c.z)))
    ctx.part(body, TORSO_SPEC)
    ctx.part(tube(f"{T} neck", [(0, 0.01, 4.26), (0, 0.02, 4.40), (0, 0.03, 4.54)], [0.20, 0.17, 0.16], [M["void"]],
                  n=16, per=2), rigid("Neck"))
    ctx.part(ellipsoid(f"{T} head void", (0, -0.01, 4.74), (0.25, 0.25, 0.34), [M["void"]], 24, 16), rigid("Head"))
    # 胸腹甲：黑玻璃弧板 + 金边 + 竖眼 + 金芒 + 电路嵌线
    pl = surface(f"{T} plackart", plack_pt, 28, 16, [M["glass"]])
    orient(pl, lambda c: Vector((0, 0.01, c.z)))
    ctx.part(finish(pl, 0.012, 1, 0), TORSO_SPEC)
    loop = [plack_pt(i / 27, 0.0, 0.014) for i in range(28)] + [plack_pt(1.0, j / 15, 0.014) for j in range(1, 16)]
    loop += [plack_pt(1 - i / 27, 1.0, 0.014) for i in range(1, 28)] + [plack_pt(0.0, 1 - j / 15, 0.014) for j in range(1, 15)]
    ctx.part(trim(f"{T} plackart rim", loop, 0.011, M["trim"], closed=True, n=4, per=1), TORSO_SPEC)
    zc = 3.42
    vc = (3.80 - zc) / (3.80 - 2.96)
    ec = plack_pt(0.5, vc, 0.004)
    eye(ctx, M, f"{T} chest eye", ec, (0, 1, 0.05), (0, 0, 1), 0.13, 0.050, TORSO_SPEC, tilt=math.pi / 2, rim=0.010)
    for i in range(12):
        ang = i * TAU / 12
        d = Vector((math.sin(ang), 0, math.cos(ang)))
        b = (d.x * 0.085, zc + d.z * 0.170)
        L = 0.11 if i % 2 == 0 else 0.06
        tp = (b[0] + d.x * L, b[1] + d.z * L)
        g = 0.022 + 0.018 * math.sin(math.pi * vc) + 0.006
        ctx.part(spike(f"{T} chest ray {i}", front_pt(b[0], b[1], g), front_pt(tp[0], tp[1], g), 0.011, [M["trim"]],
                       sides=4, up=(0, 1, 0)), TORSO_SPEC)
    for sd in (-1, 1):
        for path in ([(0.12, 3.64), (0.20, 3.64), (0.27, 3.57), (0.27, 3.30)],
                     [(0.10, 3.20), (0.17, 3.13), (0.33, 3.13)],
                     [(0.16, 3.44), (0.31, 3.44), (0.37, 3.38)]):
            pts = [front_pt(sd * x, z, 0.044) for x, z in path]
            ctx.part(trim(f"{T} chest inlay {sd}{path[0]}", pts, 0.006, M["inlay"], n=4, per=1), TORSO_SPEC)
            ctx.part(gem(f"{T} chest via {sd}{path[0]}", pts[-1], 0.012, M["glow"], (1, 0.6, 1)), TORSO_SPEC)
    # 腰间金束带（压住长袍上缘）
    cin = surface(f"{T} cincture", lambda u, v: torso_pt(u * TAU, lerp(3.02, 2.90, v), 0.036), 64, 3, [M["gilt"]],
                  closed_u=True, uvfn=lambda u, v: (u * 6, v * 0.15))
    orient(cin, lambda c: Vector((0, 0.01, c.z)))
    ctx.part(finish(cin, 0.014, 1, 0), rigid("Pelvis"))
    for z in (3.02, 2.90):
        ctx.part(trim(f"{T} cincture rim {z}", [torso_pt(i / 48 * TAU, z, 0.052) for i in range(48)], 0.009, M["trim"],
                      closed=True, n=4, per=1), rigid("Pelvis"))
    for k in range(8):
        ctx.part(gem(f"{T} cincture gem {k}", torso_pt(k * TAU / 8, 2.96, 0.054), 0.020, M["glow"], (1, 0.6, 1)),
                 rigid("Pelvis"))
    # 衬袍：从腰间落进祭台面的兰紫缎筒
    def under(u, v):
        a = u * TAU
        e = v ** 1.3
        fold = 0.012 * crest(a * 7 + 0.4) * v
        return Vector(((lerp(0.36, 0.80, e) + fold) * math.sin(a), (lerp(0.30, 0.80, e) + fold) * math.cos(a),
                       lerp(2.95, 1.79, v)))
    ur = surface(f"{T} underrobe", under, 64, 16, [M["lining"]], closed_u=True)
    orient(ur, lambda c: Vector((0, 0, c.z)))
    ctx.part(finish(ur, 0.010, -1, 0), rigid("Pelvis"))
    # 前襟开口里可见的竖向光线与两道金箍（只做前半圈）
    for a in (-0.52, -0.26, 0.26, 0.52):
        ctx.part(trim(f"{T} underrobe light {a}", [radial(under(a / TAU % 1.0, v), 0.004) for v in
                                                   [0.04 + 0.92 * i / 9 for i in range(10)]], 0.006, M["inlay"], n=4), rigid("Pelvis"))
    for v in (0.35, 0.72):
        arc = [radial(under((lerp(-0.75, 0.75, i / 20) / TAU) % 1.0, v), 0.006) for i in range(21)]
        ctx.part(trim(f"{T} underrobe band {v}", arc, 0.010, M["trim"], n=4), rigid("Pelvis"))


# ===== 披肩（肩部按距离混合上臂，抬臂时随之掀起） =====
MRX = [(3.70, 1.00), (3.80, 1.00), (3.98, 0.96), (4.16, 0.84), (4.28, 0.66), (4.36, 0.42), (4.42, 0.18)]
MRY = [(3.70, 0.55), (3.80, 0.54), (3.98, 0.52), (4.16, 0.47), (4.28, 0.40), (4.36, 0.30), (4.42, 0.17)]


def mantle_bottom(u):
    return 3.74 + 0.12 * math.sin(u * TAU) ** 2 - 0.18 * tail_weight(u, 8)


def mantle_pt(u, v):
    a = u * TAU
    z = lerp(4.42, mantle_bottom(u), v)
    rx, ry = interp(MRX, z), interp(MRY, z)
    tip = tail_weight(u, 8)
    fold = 0.022 * crest(a * 8 + 0.3) * smoothstep(4.25, 3.85, z) + 0.035 * tip * smoothstep(0.7, 1.0, v)
    return Vector(((rx + fold) * math.sin(a), 0.01 + (ry + fold) * math.cos(a), z))


def mantle_w(p):
    w = 0.6 * smoothstep(0.40, 0.85, abs(p.x))
    return {"Chest": 1 - w, f"UpperArm.{'R' if p.x > 0 else 'L'}": w}


def build_mantle(ctx, M):
    T, sp = ctx.title, fn(mantle_w)
    m = surface(f"{T} mantle", mantle_pt, 112, 20, [M["robe"], M["lining"]], closed_u=True,
                uvfn=lambda u, v: (u * 2, 0.62 * (1 - v)))
    orient(m, lambda c: Vector((0, 0.01, c.z)))
    solidify(m, 0.014, -1, inner_offset=1)
    ctx.part(apply_all(m), sp)
    n = 176
    ctx.part(trim(f"{T} mantle hem", [radial(mantle_pt(i / n, 1.0), 0.008, 0.01) for i in range(n)], 0.012, M["trim"],
                  closed=True, n=4, per=1), sp)
    ctx.part(trim(f"{T} mantle hem light", [radial(mantle_pt(i / n, 0.93), 0.006, 0.01) for i in range(n)], 0.006,
                  M["hem"], closed=True, n=4, per=1), sp)
    ctx.part(tube(f"{T} mantle collar", [radial(mantle_pt(i / 72, 0.06), 0.006, 0.01) for i in range(72)], [0.012] * 72,
                  [M["gold"]], n=5, closed=True, per=1), sp)
    for k in (0, 1, 3, 4, 6, 7):
        u = (k + 0.5) / 8
        p, nrm, up = surf_frame(mantle_pt, u, 0.80, out=lambda q: Vector((q.x, q.y - 0.01, 0.2)))
        eye(ctx, M, f"{T} mantle eye {k}", p + nrm * 0.010, nrm, up, 0.062, 0.025, sp, lash=0.03)


# ===== 手臂：钟形大袖 + 金护腕 + 黑晶利爪 + 掌心之眼 =====
def arm_rest(side):
    S = Vector((0.62 * side, 0.0, 4.02))
    E = Vector((1.00 * side, 0.26, 3.30))
    W = Vector((1.10 * side, 0.76, 3.62))
    dh = Vector((0.10 * side, 0.12, 1.0)).normalized()
    pn = Vector((0, 1, 0))
    pn = (pn - dh * pn.dot(dh)).normalized()
    return S, E, W, W + dh * (0.44 * HS), dh, pn


def build_arms(ctx, M):
    T = ctx.title
    for side, label in SIDES:
        S, E, W, Tt, dh, pn = arm_rest(side)
        arm = invdist([f"UpperArm.{label}", f"Forearm.{label}"], win=0.12)
        pts = [S + Vector((-0.16 * side, 0.0, 0.03)), S, S.lerp(E, 0.5), E, E.lerp(W, 0.30), E.lerp(W, 0.55),
               E.lerp(W, 0.78)]
        sl = sweep(f"{T} sleeve {label}", pts, [0.13, 0.155, 0.150, 0.145, 0.165, 0.215, 0.285], [M["robe"], M["lining"]],
                   nu=24, per=4, uv=(1.0, 0.6))
        solidify(sl, 0.016, -1, inner_offset=1)
        ctx.part(apply_all(sl), arm)
        fdir = (W - E).normalized()
        a1 = Vector((0, 0, 1)).cross(fdir).normalized()
        a2 = fdir.cross(a1)
        mouth = E.lerp(W, 0.78)
        ring = lambda c, r, n: [c + (a1 * math.cos(TAU * i / n) + a2 * math.sin(TAU * i / n)) * r for i in range(n)]
        ctx.part(tube(f"{T} sleeve rim {label}", ring(mouth, 0.292, 48), [0.018] * 48, [M["gold"]], n=6, closed=True,
                      per=1), rigid(f"Forearm.{label}"))
        ctx.part(trim(f"{T} sleeve light {label}", ring(E.lerp(W, 0.74), 0.27, 48), 0.007, M["hem"], closed=True, n=4,
                      per=1), rigid(f"Forearm.{label}"))
        vb = sweep(f"{T} vambrace {label}", [E.lerp(W, 0.50), E.lerp(W, 0.80), W + fdir * 0.02], [0.085, 0.080, 0.070],
                   [M["gilt"]], nu=14, per=3)
        ctx.part(finish(vb, 0.008, -1, 0), rigid(f"Forearm.{label}"))
        ctx.part(trim(f"{T} cuff {label}", ring(W + fdir * 0.02, 0.078, 24), 0.013, M["trim"], closed=True, per=1),
                 rigid(f"Forearm.{label}"))
        hs = rigid(f"Hand.{label}")
        xl = pn.cross(dh).normalized()
        ctx.part(oriented_ellipsoid(f"{T} palm {label}", W + dh * (0.13 * HS), (0.085 * HS, 0.040 * HS, 0.12 * HS),
                                    (xl, pn, dh), [M["glass"]]), hs)
        ctx.part(oriented_ellipsoid(f"{T} hand plate {label}", W + dh * (0.12 * HS) - pn * (0.018 * HS),
                                    (0.080 * HS, 0.028 * HS, 0.10 * HS), (xl, pn, dh), [M["gold"]]), hs)
        for i, L in enumerate((0.27, 0.31, 0.29, 0.24)):
            off = -side * (0.058 - 0.0387 * i) * HS
            K = W + dh * (0.23 * HS) + xl * off
            fd = (dh + xl * (off * 1.4 / HS)).normalized()
            ctx.part(spike(f"{T} claw {label}{i}", K, K + fd * (L * HS) + pn * (0.06 * HS), 0.024 * HS, [M["glass"]],
                           sides=5, up=tuple(pn), bend=0.035 * HS), hs)
            ctx.part(gem(f"{T} knuckle {label}{i}", K, 0.028 * HS, M["gold"], (1, 1, 1)), hs)
            ctx.part(gem(f"{T} claw tip glow {label}{i}", K + fd * (L * 0.55 * HS) + pn * (0.045 * HS), 0.011, M["glow"],
                         (1, 1, 1)), hs)
        Kt = W + dh * (0.08 * HS) + xl * (-side * 0.075 * HS) + pn * (0.02 * HS)
        ctx.part(spike(f"{T} thumb {label}", Kt, Kt + (xl * (-side * 0.8) + dh * 0.6 + pn * 0.25).normalized() * (0.20 * HS),
                       0.026 * HS, [M["glass"]], sides=5, up=tuple(pn), bend=0.02 * HS), hs)
        eye(ctx, M, f"{T} palm eye {label}", W + dh * (0.13 * HS) + pn * (0.040 * HS), pn, dh, 0.052 * HS, 0.024 * HS, hs,
            rim=0.007)


# ===== 兜帽：下半兜（Head）+ 左右冠瓣（HoodL / HoodR，狂暴时裂开）=====
HR = [(0.0, 0.015), (0.07, 0.12), (0.18, 0.25), (0.32, 0.37), (0.46, 0.45), (0.62, 0.49), (0.80, 0.52), (1.0, 0.57)]
HY = [(0.0, -0.34), (0.18, -0.21), (0.35, -0.10), (0.52, -0.03), (0.7, 0.0), (1.0, -0.03)]
HSY = [(0.0, 1.0), (0.3, 1.12), (0.6, 1.17), (1.0, 1.06)]
HOP = [(0.0, 0.02), (0.36, 0.025), (0.42, 0.28), (0.48, 0.60), (0.56, 0.82), (0.68, 0.90), (0.80, 0.84), (0.90, 0.62),
       (1.0, 0.46)]


def hop(v):
    return interp(HOP, v)


def hood_v(z):
    return (HOOD_TOP - z) / (HOOD_TOP - HOOD_BOT)


def hood_pt(a, v):
    """a 绕轴角（0 正前、增大转向 +X），v 自顶点向下 0→1。"""
    z = lerp(HOOD_TOP, HOOD_BOT, v)
    r, yo, sy = interp(HR, v), interp(HY, v), interp(HSY, v)
    op = hop(v)
    fold = 0.014 * crest(a * 5 + 0.5) * smoothstep(0.55, 1.0, v)
    ridge = 0.022 * math.exp(-((a - math.pi) / 0.12) ** 2) * (1 - smoothstep(0.1, 0.6, v)) * smoothstep(0.0, 0.08, v)
    e = min(a - op, TAU - op - a)
    lip = 0.018 * math.exp(-max(0.0, e) / 0.05) * smoothstep(0.38, 0.48, v)
    rr = r + fold + ridge + lip
    return Vector((rr * math.sin(a), yo + rr * math.cos(a) * sy, z))


def hood_out(q):
    return Vector((q.x, q.y - interp(HY, hood_v(q.z)), 0.0))


def hood_hinge(side):
    return Vector((side * 0.47, -0.03, HOOD_SPLIT))


def hood_piece(ctx, M, name, a_lo, a_hi, v0, v1, spec, nu, nv):
    def pt(u, w):
        v = lerp(v0, v1, w)
        return hood_pt(lerp(a_lo(v), a_hi(v), u), v)

    def uv(u, w):
        v = lerp(v0, v1, w)
        return (lerp(a_lo(v), a_hi(v), u) / TAU * 2.0, 0.28 + 0.50 * (1 - v))
    obj = surface(name, pt, nu, nv, [M["robe"], M["void"], M["trim"]], uvfn=uv)
    orient(obj, lambda c: Vector((0, interp(HY, hood_v(c.z)), c.z)))
    solidify(obj, 0.028, -1, inner_offset=1, rim_offset=2)
    ctx.part(apply_all(obj), spec)


def hood_line(ctx, M, name, pts_av, rad, mat, spec, lift=0.010):
    pts = [radial(hood_pt(a, v), lift, interp(HY, v)) for a, v in pts_av]
    ctx.part(trim(name, pts, rad, M[mat], n=4), spec)


def hood_eye(ctx, M, name, a, v, w, h, spec, lash=0.0):
    p, n, up = surf_frame(lambda uu, vv: hood_pt(uu * TAU, vv), a / TAU, v, out=hood_out)
    eye(ctx, M, name, p + n * 0.006, n, up, w, h, spec, lash=lash)


def build_hood(ctx, M):
    T = ctx.title
    head = rigid("Head")
    hood_piece(ctx, M, f"{T} hood cowl", hop, lambda v: TAU - hop(v), VS, 1.0, head, 72, 18)
    hood_piece(ctx, M, f"{T} hood crown R", hop, lambda v: math.pi, 0.0, VS, rigid("HoodR"), 30, 34)
    hood_piece(ctx, M, f"{T} hood crown L", lambda v: math.pi, lambda v: TAU - hop(v), 0.0, VS, rigid("HoodL"), 30, 34)
    # 分割线处的金冠带（留在下半兜上）
    a0, a1 = hop(VS) + 0.03, TAU - hop(VS) - 0.03

    def band_pt(u, w):
        v = VS + 0.05 * w
        return radial(hood_pt(lerp(a0, a1, u), v), 0.012, interp(HY, v))
    band = surface(f"{T} circlet", band_pt, 64, 3, [M["gilt"]], uvfn=lambda u, w: (u * 4, w * 0.2))
    orient(band, lambda c: Vector((0, interp(HY, VS), c.z)))
    ctx.part(finish(band, 0.012, 1, 0), head)
    for w in (0.0, 1.0):
        ctx.part(trim(f"{T} circlet rim {w}", [radial(band_pt(i / 43, w), 0.012, interp(HY, VS)) for i in range(44)],
                      0.008, M["trim"], n=4), head)
    for sd in (-1, 1):
        a = hop(VS) + 0.05 if sd > 0 else TAU - hop(VS) - 0.05
        c = radial(hood_pt(a, VS + 0.025), 0.03, interp(HY, VS))
        ctx.part(gem(f"{T} circlet medallion {sd}", c, 0.034, M["gold"], (1, 1, 1)), head)
        ctx.part(gem(f"{T} circlet gem {sd}", radial(c, 0.026, interp(HY, VS)), 0.016, M["glow"], (1, 1, 1)), head)
    # 冠瓣接缝的双金脊（裂开时一分为二）、开口内侧光缝
    vs_line = [0.03 + (VS - 0.03) * i / 24 for i in range(25)]
    for label, sd in (("R", 1), ("L", -1)):
        sp = rigid(f"Hood{label}")
        back = [(math.pi - sd * 0.03, v) for v in vs_line]
        hood_line(ctx, M, f"{T} crown seam back {label}", back, 0.010, "trim", sp)
        fv = [0.03 + 0.37 * i / 14 for i in range(15)]
        front = [((hop(v) + 0.03) if sd > 0 else (TAU - hop(v) - 0.03), v) for v in fv]
        hood_line(ctx, M, f"{T} crown seam front {label}", front, 0.010, "trim", sp)
        lv = [0.42 + (VS - 0.42) * i / 10 for i in range(11)]
        edge = [((hop(v) + 0.07) if sd > 0 else (TAU - hop(v) - 0.07), v) for v in lv]
        hood_line(ctx, M, f"{T} crown edge light {label}", edge, 0.006, "inlay", sp, lift=0.004)
        cv = [VS + 0.07 + (1.0 - VS - 0.09) * i / 16 for i in range(17)]
        edge2 = [((hop(v) + 0.07) if sd > 0 else (TAU - hop(v) - 0.07), v) for v in cv]
        hood_line(ctx, M, f"{T} cowl edge light {label}", edge2, 0.006, "inlay", head, lift=0.004)
        for j, (a, v, w, h, lash) in enumerate(((0.42, 0.22, 0.060, 0.024, 0.03), (0.92, 0.34, 0.068, 0.027, 0.04),
                                                (1.42, 0.44, 0.064, 0.026, 0.0), (1.30, 0.18, 0.050, 0.020, 0.0),
                                                (1.95, 0.32, 0.058, 0.023, 0.0))):
            hood_eye(ctx, M, f"{T} crown eye {label}{j}", a if sd > 0 else TAU - a, v, w, h, sp, lash)
        for j, (a, v, w, h) in enumerate(((1.55, 0.80, 0.060, 0.024), (2.25, 0.72, 0.055, 0.022))):
            hood_eye(ctx, M, f"{T} cowl eye {label}{j}", a if sd > 0 else TAU - a, v, w, h, head)
        # 冠瓣内壁的眼：合拢时朝内藏住，裂开后朝上露出
        for j, (a, v, w, h) in enumerate(((1.30, 0.28, 0.070, 0.028), (1.90, 0.38, 0.074, 0.030),
                                          (2.50, 0.30, 0.066, 0.026))):
            aa = a if sd > 0 else TAU - a
            p, n, up = surf_frame(lambda uu, vv: hood_pt(uu * TAU, vv), aa / TAU, v, out=hood_out)
            eye(ctx, M, f"{T} crown inner eye {label}{j}", p - n * 0.034, -n, up, w, h, sp)
    hood_eye(ctx, M, f"{T} cowl eye back", math.pi, 0.78, 0.07, 0.028, head, 0.04)


def build_crest(ctx, M):
    """头顶眼冠（藏在冠瓣内，狂暴时冠瓣裂开并升起）。"""
    T, sp = ctx.title, rigid("Crest")
    c = CREST_C
    rx, ry, rz = 0.30, 0.27, 0.19
    ctx.part(ellipsoid(f"{T} eye crest", c, (rx, ry, rz), [M["void"]], 28, 14), sp)
    for j in range(6):
        az = j * TAU / 6 + math.pi / 6
        arc = []
        for i in range(9):
            el = lerp(0.05, 1.45, i / 8)
            arc.append(c + Vector((rx * math.cos(el) * math.sin(az), ry * math.cos(el) * math.cos(az), rz * math.sin(el))) * 1.0
                       + Vector((math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el))) * 0.006)
        ctx.part(trim(f"{T} crest vein {j}", arc, 0.008, M["trim"], n=4), sp)
    base = [c + Vector((rx * math.cos(0.10) * math.sin(q), ry * math.cos(0.10) * math.cos(q), rz * math.sin(0.10)))
            * 1.0 + Vector((math.sin(q), math.cos(q), 0)) * 0.010 for q in [i / 40 * TAU for i in range(40)]]
    ctx.part(trim(f"{T} crest halo", base, 0.011, M["glow"], closed=True, n=4, per=1), sp)
    # 顶眼 + 上圈五眼 + 下圈四眼；正面方位避开面孔开口的视线（静止时藏在冠瓣里）
    spots = [(0.0, 1.35, 0.085, 0.034)] + [(az, 0.90, 0.074, 0.029) for az in (0.80, -0.80, 1.75, -1.75, math.pi)]
    spots += [(az, 0.38, 0.066, 0.026) for az in (1.50, -1.50, 2.40, -2.40)]
    for j, (az, el, w, h) in enumerate(spots):
        d = Vector((math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)))
        p = c + Vector((rx * d.x, ry * d.y, rz * d.z))
        nrm = Vector((d.x / rx, d.y / ry, d.z / rz)).normalized()
        eye(ctx, M, f"{T} crest eye {j}", p + nrm * 0.004, nrm, (0, 1, 0) if j == 0 else (0, 0, 1), w, h, sp, lash=0.02)


# ===== 骨瓷面具（七眼 + 泪痕光线 + 金眉） =====
def build_mask(ctx, M):
    T, sp = ctx.title, rigid("Head")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=36, v_segments=26, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.02], context="VERTS")
    for v in bm.verts:
        x, y, z = v.co
        if z < 0:                                   # 下颌拉长收尖
            z *= 1.22
            k = (-z) ** 1.35
            x *= max(0.08, 1 - 0.66 * k)
            y += 0.16 * k * max(0.0, y)
        if z > 0.45:
            z = 0.45 + (z - 0.45) * 0.55              # 压低额顶
        x *= 1 - 0.07 * (1 - abs(z))
        front = max(0.0, y)
        prow = 0.10 * math.exp(-(x / 0.18) ** 2) * front
        brow = 0.06 * math.exp(-((z - 0.26) / 0.08) ** 2) * front
        cheek = -0.04 * math.exp(-((z + 0.05) / 0.12) ** 2) * math.exp(-((abs(x) - 0.55) / 0.2) ** 2) * front
        v.co = Vector((x * 0.205, (y + prow + brow + cheek) * 0.165, z * 0.29)) + MASK_C
    mask = bm_object(f"{T} mask", bm, [M["mask"]])
    orient(mask, lambda c: MASK_C - Vector((0, 0.05, 0)))
    solidify(mask, 0.014, -1)
    subsurf(mask, 1)
    apply_all(mask)
    ctx.part(mask, sp)
    bvh = BVHTree.FromObject(mask, bpy.context.evaluated_depsgraph_get())

    def hit(x, z, lift=0.0):
        loc, nrm, _, _ = bvh.ray_cast(Vector((x, MASK_C.y + 1.0, z)), Vector((0, -1, 0)))
        if loc is None:
            return Vector((x, MASK_C.y + 0.15, z)), Vector((0, 1, 0))
        if nrm.y < 0:
            nrm = -nrm
        return loc + nrm * lift, nrm
    for k, loop in enumerate(boundary_loops(mask)):
        if len(loop) > 12:
            ctx.part(trim(f"{T} mask rim {k}", loop, 0.006, M["trim"], closed=True, n=4, per=1), sp)
    p, n = hit(0.0, 4.885, 0.002)
    eye(ctx, M, f"{T} third eye", p, n, (0, 0, 1), 0.052, 0.022, sp, tilt=math.pi / 2, rim=0.005)
    for sd in (-1, 1):
        for j, (x, z, w, h, tl, lash) in enumerate(((0.082, 4.795, 0.052, 0.021, 0.20, 0.03),
                                                    (0.070, 4.700, 0.038, 0.015, -0.12, 0.0),
                                                    (0.140, 4.745, 0.028, 0.012, 0.30, 0.0))):
            p, n = hit(sd * x, z, 0.002)
            eye(ctx, M, f"{T} mask eye {sd}{j}", p, n, (0, 0, 1), w, h, sp, tilt=-sd * tl, rim=0.0045, lash=lash)
        brow = [hit(sd * x, 4.838 + 0.012 * math.sin(math.pi * (x - 0.03) / 0.15), 0.003)[0]
                for x in [0.03 + 0.15 * i / 10 for i in range(11)]]
        ctx.part(trim(f"{T} mask brow {sd}", brow, 0.0055, M["trim"], n=4), sp)
        tear = [hit(sd * (0.080 + 0.012 * math.sin(i * 0.9)), 4.772 - i * 0.022, 0.0025)[0] for i in range(10)]
        ctx.part(trim(f"{T} mask tear {sd}", tear, 0.0042, M["inlay"], n=4), sp)
    p, n = hit(0.0, 4.52, 0.002)
    eye(ctx, M, f"{T} chin eye", p, n, (0, 0, 1), 0.034, 0.013, sp, rim=0.004)
    ridge = [hit(0.0, 4.845 - i * 0.02, 0.003)[0] for i in range(9)]
    ctx.part(trim(f"{T} mask ridge", ridge, 0.005, M["trim"], n=4), sp)


# ===== 光环（挂 Halo 骨，六重对称，绕 Y 轴自转） =====
def build_halo(ctx, M):
    T, sp = ctx.title, rigid("Halo")
    c = HALO_C

    def at(a, r, dy=0.0):
        return c + Vector((math.sin(a) * r, dy, math.cos(a) * r))
    circ = lambda r, n, dy=0.0: [at(i / n * TAU, r, dy) for i in range(n)]
    ctx.part(tube(f"{T} halo rim", circ(HALO_R, 96), [0.028] * 96, [M["gold"]], n=8, closed=True, per=1), sp)
    ctx.part(tube(f"{T} halo inner rim", circ(0.80, 72), [0.018] * 72, [M["gold"]], n=6, closed=True, per=1), sp)
    ctx.part(trim(f"{T} halo light", circ(0.73, 72), 0.007, M["inlay"], closed=True, n=4, per=1), sp)
    ctx.part(flat_ring(f"{T} halo band", c, 0.82, 0.96, [M["rune"]], seg=120, thick=0.012, normal=(0, 1, 0),
                       au=(1, 0, 0), av=(0, 0, 1), uvfn=lambda u, v: (u * 6, 0.25 + 0.25 * v)), sp)
    for k in range(12):
        a = k * TAU / 12
        if k % 2 == 0:
            ctx.part(spike(f"{T} halo ray {k}", at(a, HALO_R), at(a, 1.50), 0.055, [M["glass"]], sides=4, fx=0.3, fy=1.0,
                           up=(0, 1, 0)), sp)
            ctx.part(trim(f"{T} halo ray light {k}", [at(a, 1.06, 0.019), at(a, 1.38, 0.019)], 0.006, M["inlay"], n=4,
                          per=1), sp)
        else:
            ctx.part(spike(f"{T} halo spur {k}", at(a, HALO_R), at(a, 1.24), 0.032, [M["trim"]], sides=4), sp)
    for k in range(6):
        a = k * TAU / 6 + math.pi / 6
        eye(ctx, M, f"{T} halo eye {k}", at(a, 0.89, 0.010), (0, 1, 0), (math.sin(a), 0, math.cos(a)), 0.072, 0.030,
            sp, lash=0.03)


# ===== 长袍与圣带 =====
RB = [(0.0, 0.405), (0.12, 0.50), (0.25, 0.68), (0.40, 0.95), (0.55, 1.22), (0.68, 1.40), (0.80, 1.49), (1.0, 1.56)]


def robe_r(u, v, a):
    r = interp(RB, v)
    return r, r * lerp(0.85, 1.0, smoothstep(0.0, 0.45, v))


def cloth():
    robe = Wrap("Robe", "Pelvis", 0.62, TAU - 0.62, top=2.955, bottom=1.60, r_top=(0.405, 0.345), r_bot=(1.56, 1.56),
                K=8, joints=(0, 0.16, 0.34, 0.52, 0.74, 1.0), cy=0.0, flow=0.0, widen=0.0,
                folds=(7.0, 0.008, 0.040), seed=1.7, tails=8, tail_len=(0.12, 0.05), curl=(0.03, 0.01),
                radius_fn=robe_r)
    stole = Panel("Stole", "Pelvis", 2.97, 2.02, [(0, 0.30), (0.5, 0.31), (1.0, 0.24)],
                  [(0, 0.37), (0.3, 0.50), (0.6, 0.64), (1.0, 0.78)], side=1, K=1, joints=(0, 0.30, 0.62, 1.0),
                  curve=0.9, point=0.16)
    return robe, stole


def build_robe(ctx, M, robe):
    T, sp = ctx.title, garment(robe)
    robe.build(ctx, [M["robe"], M["lining"]], f"{T} robe", nu=128, nv=46, thickness=0.014, uv_scale=3.0)
    for u in (0.0, 1.0):
        pts = [radial(robe.point(u, j / 36), 0.005) for j in range(37)]
        ctx.part(trim(f"{T} robe edge {u}", pts, 0.014, M["trim"], n=4, per=1), sp)
    n = 192
    ctx.part(trim(f"{T} robe hem", [radial(robe.point(i / (n - 1), 1.0), 0.006) for i in range(n)], 0.011, M["hem"],
                  n=4, per=1), sp)
    ctx.part(trim(f"{T} robe gilt hem", [radial(robe.point(i / (n - 1), 0.955), 0.009) for i in range(n)], 0.009,
                  M["trim"], n=4, per=1), sp)
    for k in range(robe.K):
        u = (k + 0.5) / robe.K
        p, nrm, up = surf_frame(robe.point, u, 0.50, out=lambda q: Vector((q.x, q.y, 0.6)))
        eye(ctx, M, f"{T} robe eye {k}", p + nrm * 0.014, nrm, up, 0.125, 0.048, sp, lash=0.07, rim=0.010)


def build_stole(ctx, M, stole):
    T, sp = ctx.title, garment(stole)
    obj = surface(f"{T} stole", stole.point, 12, 40, [M["rune"], M["lining"]],
                  uvfn=lambda u, v: (0.10 + v * 0.83, 0.5 * u))
    orient(obj, lambda c: Vector((0, 0, c.z)))
    solidify(obj, 0.010, 0, inner_offset=1)
    ctx.part(apply_all(obj), sp)
    for u in (0.0, 1.0):
        pts = [stole.point(u, j / 26) + Vector((0, 0.006, 0)) for j in range(27)]
        ctx.part(trim(f"{T} stole edge {u}", pts, 0.012, M["trim"], n=4), sp)
    top = stole.point(0.5, 0.03) + Vector((0, 0.02, 0))
    ctx.part(ellipsoid(f"{T} stole brooch", top, (0.075, 0.025, 0.06), [M["gold"]], 20, 10), sp)
    eye(ctx, M, f"{T} brooch eye", top + Vector((0, 0.022, 0)), (0, 1, 0), (0, 0, 1), 0.045, 0.019, sp, rim=0.005)
    ctx.part(gem(f"{T} stole tip", stole.point(0.5, 1.0) + Vector((0, 0.01, -0.03)), 0.028, M["glow"], (0.7, 0.5, 1.4)), sp)


def build(ctx):
    M = materials(ctx)
    build_altar(ctx, M)
    build_well(ctx, M)
    build_chips(ctx, M)
    for k in range(N_SH):
        build_shard(ctx, M, k)
    for k in range(N_ORB):
        build_orb(ctx, M, k)
    build_body(ctx, M)
    build_mantle(ctx, M)
    build_arms(ctx, M)
    build_hood(ctx, M)
    build_crest(ctx, M)
    build_mask(ctx, M)
    build_halo(ctx, M)
    robe, stole = cloth()
    build_robe(ctx, M, robe)
    build_stole(ctx, M, stole)
    stats(ctx, GAME_TRIS)
    return {"robe": robe, "stole": stole}


# ===== 骨骼 =====
def skeleton(rig, st):
    rig.bone("Root", (0, 0, 0), (0, 0, 0.3))
    rig.bone("Well", (0, 0, 0.014), (0, 0, 0.40), "Root", roll=Y)
    rig.bone("Hover", (0, 0, 0.30), (0, 0, 0.80), "Root", roll=Y)
    rig.translate["Hover"] = "_hover"
    rig.bone("Altar", (0, 0, 0.80), (0, 0, 1.80), "Hover", roll=Y)
    rig.bone("Pelvis", (0, 0, 2.60), (0, 0, 3.05), "Altar", roll=Y)
    rig.bone("Spine", (0, 0, 3.05), (0, 0.02, 3.62), "Pelvis", roll=Y)
    rig.bone("Chest", (0, 0.02, 3.62), (0, 0.02, 4.24), "Spine", roll=Y)
    rig.bone("Neck", (0, 0.02, 4.24), (0, 0.03, 4.46), "Chest", roll=Y)
    rig.bone("Head", (0, 0.03, 4.46), (0, 0.03, 5.10), "Neck", roll=Y)
    for side, label in SIDES:
        h = hood_hinge(side)
        rig.bone(f"Hood{label}", h, h + Vector((0, 0, 0.35)), "Head", roll=Y)
        S, E, W, Tt, dh, pn = arm_rest(side)
        rig.bone(f"UpperArm.{label}", S, E, "Chest", roll=Y)
        rig.bone(f"Forearm.{label}", E, W, f"UpperArm.{label}", roll=Z)
        rig.bone(f"Hand.{label}", W, Tt, f"Forearm.{label}", roll=pn)
    rig.bone("Crest", CREST_C, CREST_C + Vector((0, 0, 0.3)), "Head", roll=Y)
    rig.translate["Crest"] = "_crest"
    rig.bone("Halo", HALO_C, HALO_C + Vector((0, -0.3, 0)), "Chest", roll=Z)
    rig.bone("OrbitS", (0, 0, 2.2), (0, 0, 2.8), "Hover", roll=Y)
    for k in range(N_SH):
        L = SHARD_T[k % 2]["L"]
        h = shard_matrix(k) @ Vector((0, 0, L * 0.5))
        rig.bone(f"Shard{k}", h, h + shard_axis(k) * 0.4, "OrbitS", roll=rd(shard_slot(k)))
        rig.translate[f"Shard{k}"] = f"_shard{k}"
    for k in range(N_ORB):
        a, c = orb_center(k)
        rig.bone(f"Orb{k}", c, c + Vector((0, 0, 0.4)), "OrbitS", roll=rd(a))
        rig.translate[f"Orb{k}"] = f"_orb{k}"
    rig.bone("OrbitC", (0, 0, 0.9), (0, 0, 1.3), "Hover", roll=Y)
    rig.add_garment(st["robe"])
    rig.add_garment(st["stole"])


# ===== 动作 =====
def ring_pose(p, t, om, halo, well, chips, ext_s=0.0, ext_o=0.0, lift_o=0.0, amp=1.0):
    """公转环：om 为公转角（槽位角 a = a0 + om），浮动 / 摆动相位取 t + a，保证三重对称下循环无缝。"""
    p["OrbitS"] = R((Z, -om))
    for k in range(N_SH):
        a0 = shard_slot(k)
        a = a0 + om
        p[f"_shard{k}"] = rd(a0) * ext_s + Vector((0, 0, 0.07 * math.sin(t + a) * amp))
        p[f"Shard{k}"] = R((td(a0), 0.035 * math.sin(t + a + 1.1) * amp), (shard_axis(k), 0.22 * math.sin(t + a + 0.4) * amp))
    for k in range(N_ORB):
        a0, _ = orb_center(k)
        a = a0 + om
        p[f"_orb{k}"] = rd(a0) * ext_o + Vector((0, 0, 0.09 * math.sin(t + a + 2.0) * amp + lift_o))
        p[f"Orb{k}"] = R((Z, t))
    p["Halo"] = R((Y, halo))
    p["Well"] = R((Z, well))
    p["OrbitC"] = R((Z, chips))


def orb_pulse(t, om, k, amp=0.05):
    """待机脉动：同拍心跳（t=0 时为 1，与一次性动作首帧一致），幅度随槽位角起伏（循环仍无缝）。"""
    a0, _ = orb_center(k)
    s = 1.0 + amp * math.sin(2 * t) * (0.75 + 0.25 * math.sin(a0 + om + t))
    return (s, s, s)


def body_idle(t, amp=1.0):
    p = {"_hover": 0.05 * math.sin(t) * amp, "_crest": Vector((0, 0, 0))}
    p["Hover"] = R((X, 0.010 * math.sin(t + 0.6) * amp), (Y, 0.008 * math.sin(t + 1.9) * amp))
    p["Spine"] = R((X, 0.018 * math.sin(t + 0.4) * amp))
    p["Chest"] = R((X, 0.014 * math.sin(t + 0.9) * amp), (Z, 0.020 * math.sin(t) * amp))
    p["Neck"] = R((X, 0.010 * math.sin(t + 1.1) * amp))
    p["Head"] = R((X, 0.030 * math.sin(t + 1.3) * amp), (Z, 0.035 * math.sin(t + 0.2) * amp))
    for side, label in SIDES:
        ph = 0.0 if side > 0 else 1.7
        p[f"UpperArm.{label}"] = R((X, 0.035 * math.sin(t + ph) * amp), (Y, side * 0.03 * math.sin(t + ph + 0.8) * amp))
        p[f"Forearm.{label}"] = R((X, 0.05 * math.sin(t + ph + 0.5) * amp))
        p[f"Hand.{label}"] = R((X, 0.06 * math.sin(t + ph + 1.0) * amp))
    return p


def cloth_pose(rig, st, p, t, amp=1.0, lift=0.0, trail=0.0):
    robe = st["robe"]

    def flare(k, j):
        # 正面两条链少掀（掀起过多会从前襟开口露出大片里衬）
        a = robe.angle((k + 0.5) / robe.K)
        front = max(0.0, math.cos(a))
        return (0.025 + lift * (1 - 0.7 * front) + trail * max(0.0, -math.cos(a))
                + 0.018 * math.sin(t + k * 0.85 + j * 0.6) * amp)
    rig.garment_pose(p, robe, flare, lambda k, j: 0.012 * math.sin(t + k * 0.7) * amp)
    rig.garment_pose(p, st["stole"], lambda k, j: 0.03 + lift * 0.5 + 0.025 * math.sin(t + j * 0.8) * amp)


def idle_pose(rig, st, t):
    p = body_idle(t)
    ring_pose(p, t, t / 3, -t / 6, t / 6, -t / 6)
    cloth_pose(rig, st, p, t)
    return p


def move_pose(rig, st, t):
    p = body_idle(2 * t, 0.6)
    p["_hover"] = 0.09 + 0.045 * math.sin(2 * t)
    p["Hover"] = R((X, -0.065 + 0.012 * math.sin(2 * t + 0.8)), (Y, 0.02 * math.sin(t)))
    p["Spine"] = R((X, -0.04 + 0.01 * math.sin(2 * t)))
    p["Chest"] = R((X, -0.02), (Z, 0.03 * math.sin(t)))
    p["Head"] = R((X, 0.07), (Z, 0.02 * math.sin(t + 0.5)))
    for side, label in SIDES:
        ph = 0.0 if side > 0 else 1.7
        p[f"UpperArm.{label}"] = R((X, -0.14 + 0.03 * math.sin(2 * t + ph)), (Y, -side * 0.06))
        p[f"Forearm.{label}"] = R((X, -0.10 + 0.04 * math.sin(2 * t + ph + 0.6)))
        p[f"Hand.{label}"] = R((X, -0.12 + 0.05 * math.sin(2 * t + ph + 1.1)))
    ring_pose(p, t, t / 3, -t / 6, t / 6, -t / 6)
    cloth_pose(rig, st, p, 2 * t, 0.8, lift=0.02, trail=0.12)
    return p


def arm_aim(rig, p, side, label, du, df, dh, palm):
    rig.aim(p, f"UpperArm.{label}", Vector((du[0] * side, du[1], du[2])))
    rig.aim(p, f"Forearm.{label}", Vector((df[0] * side, df[1], df[2])))
    rest = arm_rest(side)
    rig.aim(p, f"Hand.{label}", Vector((dh[0] * side, dh[1], dh[2])), up=Vector((palm[0] * side, palm[1], palm[2])),
            rest_up=rest[5])


def key_body(rig, torso, hover, arms):
    """关键姿态：torso 为 {骨: 绕 X 的俯仰角}，arms 为 (上臂, 前臂, 手, 掌心) 方向（右侧，左侧镜像 x）。"""
    p = body_idle(0.0, 0.0)
    p["_hover"] = hover
    for name, ang in torso.items():
        p[name] = R((X, ang))
    for side, label in SIDES:
        arm_aim(rig, p, side, label, *arms)
    return p


def attack_pose(rig, st, s, keys):
    idle0, raise_, open_ = keys
    p = mix(idle0, raise_, ease(s / 0.30))
    p = mix(p, open_, ease((s - 0.30) / 0.16))
    p = mix(p, idle0, ease((s - 0.62) / 0.38))
    t = TAU * s
    om = ATK["spin"](s)
    ring_pose(p, t, om, -TAU / 3 * ease(s), TAU / 3 * ease(s), -TAU / 3 * ease(s),
              ext_s=ATK["ext_s"](s), ext_o=ATK["ext_o"](s), lift_o=ATK["lift_o"](s))
    cloth_pose(rig, st, p, t, 0.6, lift=ATK["lift"](s))
    return p


def enrage_pose(rig, st, s, keys):
    idle0, crouch, roar = keys
    p = mix(idle0, crouch, ease(s / 0.16))
    p = mix(p, roar, ease((s - 0.16) / 0.18))
    p = mix(p, idle0, ease((s - 0.78) / 0.22))
    env = smoothstep(0.30, 0.40, s) * (1 - smoothstep(0.74, 0.82, s))
    shake = 0.022 * env * math.sin(s * 95.0)
    p["Chest"] = R((Z, shake)) @ p.get("Chest", R())
    p["Head"] = R((Y, shake * 1.3)) @ p.get("Head", R())
    th = ENR["hood"](s)
    p["HoodR"] = R((Y, th))
    p["HoodL"] = R((Y, -th))
    p["_crest"] = Vector((0, -0.06 * ENR["crest"](s), ENR["crest"](s)))
    t = 2 * TAU * s
    om = ENR["spin"](s)
    ring_pose(p, t, om, -om, om, -om, ext_s=ENR["ext_s"](s), ext_o=ENR["ext_o"](s), lift_o=ENR["lift_o"](s))
    cloth_pose(rig, st, p, t, 0.7, lift=ENR["lift"](s))
    return p


ATK = {"ext_o": Track([(0, 0.0), (0.28, -0.22), (0.46, 0.85), (0.62, 0.75), (1.0, 0.0)]),
       "lift_o": Track([(0, 0.0), (0.28, 0.25), (0.46, 0.10), (1.0, 0.0)]),
       "ext_s": Track([(0, 0.0), (0.30, -0.05), (0.48, 0.15), (1.0, 0.0)]),
       "lift": Track([(0, 0.0), (0.30, 0.03), (0.46, 0.16), (0.62, 0.12), (1.0, 0.0)]),
       "orb": Track([(0, 1.0), (0.28, 0.82), (0.46, 1.55), (0.56, 1.30), (0.66, 1.45), (1.0, 1.0)]),
       "well": Track([(0, 1.0), (0.30, 0.95), (0.50, 1.60), (0.70, 1.45), (1.0, 1.0)]),
       "spin": spin_curve(lambda q: 0.4 + 2.5 * math.exp(-((q - 0.45) / 0.12) ** 2), TAU / 3)}
ENR = {"hood": Track([(0, 0.0), (0.12, 0.05), (0.32, 0.70), (0.76, 0.66), (0.95, 0.0), (1.0, 0.0)]),
       "crest": Track([(0, 0.0), (0.18, 0.0), (0.38, 0.32), (0.76, 0.30), (0.95, 0.0), (1.0, 0.0)]),
       "ext_s": Track([(0, 0.0), (0.16, -0.08), (0.36, 0.38), (0.78, 0.32), (1.0, 0.0)]),
       "ext_o": Track([(0, 0.0), (0.16, -0.10), (0.36, 0.45), (0.78, 0.40), (1.0, 0.0)]),
       "lift_o": Track([(0, 0.0), (0.36, 0.25), (0.78, 0.20), (1.0, 0.0)]),
       "lift": Track([(0, 0.0), (0.36, 0.14), (0.78, 0.10), (1.0, 0.0)]),
       "orb": Track([(0, 1.0), (0.16, 0.90), (0.36, 1.35), (0.78, 1.25), (1.0, 1.0)]),
       "well": Track([(0, 1.0), (0.36, 1.25), (0.78, 1.20), (1.0, 1.0)]),
       "spin": spin_curve(lambda q: 0.25 + 3.0 * smoothstep(0.10, 0.45, q) * (1 - smoothstep(0.78, 0.98, q)), TAU)}


def animate(rig, st):
    rig.loop("Idle", 120, lambda t: idle_pose(rig, st, t), step=2)
    key_scale(rig, range(1, 122, 2), lambda f: dict(
        {f"Orb{k}": orb_pulse(TAU * (f - 1) / 120, TAU * (f - 1) / 360, k) for k in range(N_ORB)}, Well=(1, 1, 1)))
    rig.loop("Move", 96, lambda t: move_pose(rig, st, t), step=2)
    key_scale(rig, range(1, 98, 2), lambda f: dict(
        {f"Orb{k}": orb_pulse(TAU * (f - 1) / 96, TAU * (f - 1) / 288, k) for k in range(N_ORB)}, Well=(1, 1, 1)))
    idle0 = idle_pose(rig, st, 0.0)
    raise_ = key_body(rig, {"Spine": 0.06, "Chest": 0.08, "Head": 0.10}, 0.10,
                      ((0.62, 0.30, 0.72), (0.22, 0.38, 0.90), (0.08, 0.30, 0.95), (0.0, 0.95, -0.30)))
    open_ = key_body(rig, {"Spine": -0.07, "Chest": -0.06, "Head": -0.04}, 0.02,
                     ((0.75, 0.45, -0.48), (0.60, 0.72, -0.35), (0.45, 0.80, -0.40), (0.0, 0.35, -0.94)))
    for q in (raise_, open_):
        cloth_pose(rig, st, q, 0.0, 0.0)
    rig.sampled("Attack", 32, lambda s: attack_pose(rig, st, s, (idle0, raise_, open_)))
    key_scale(rig, range(1, 34), lambda f: dict(
        {f"Orb{k}": (ATK["orb"]((f - 1) / 32),) * 3 for k in range(N_ORB)},
        Well=(ATK["well"]((f - 1) / 32), 1.0, ATK["well"]((f - 1) / 32))))
    crouch = key_body(rig, {"Spine": -0.10, "Chest": -0.10, "Head": -0.12}, -0.04,
                      ((0.25, 0.35, -0.90), (-0.05, 0.85, 0.52), (0.0, 0.20, 0.98), (0.0, 1.0, -0.2)))
    roar = key_body(rig, {"Spine": 0.08, "Chest": 0.12, "Neck": 0.08, "Head": 0.16}, 0.18,
                    ((0.80, 0.22, 0.52), (0.38, 0.22, 0.90), (0.20, 0.25, 0.95), (0.0, 0.95, -0.25)))
    for q in (crouch, roar):
        cloth_pose(rig, st, q, 0.0, 0.0)
    rig.sampled("Enrage", 48, lambda s: enrage_pose(rig, st, s, (idle0, crouch, roar)))
    key_scale(rig, range(1, 50), lambda f: dict(
        {f"Orb{k}": (ENR["orb"]((f - 1) / 48) + 0.06 * math.sin(TAU * 3 * (f - 1) / 48 + k)
                     * math.sin(math.pi * (f - 1) / 48),) * 3 for k in range(N_ORB)},
        Well=(ENR["well"]((f - 1) / 48), 1.0, ENR["well"]((f - 1) / 48))))
