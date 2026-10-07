"""沃尔特 · 风暴圣殿骑士（Volt, The Storm Templar）。

设定：深海军蓝漆甲 + 亮银 + 电蓝白光。流线高盔带 Y 形光缝、后掠鳍冠与避雷针，太阳穴伸出两根后掠避雷角；
双肩后方各立一座特斯拉线圈塔（堆叠光环 + 环形顶载 + 放电弧，终结技时外展升起）；胸口闪电纹章与银色人字甲，
分节腹甲；四肢漆甲带导电电路纹、外侧银色疾风鳍；身后左右分开的短披风（风暴闪电纹）。
动作：Idle（蓄势待机）/ Move（冲刺跑）/ Cast「雷隙」（爆发前冲弓步、右掌突刺）/
Channel「狼雷」（双臂高举引雷、仰首、线圈外展）。
"""

import math

from mathutils import Matrix, Vector

from kit.core import (TAU, circuit_maps, clamp, ellipsoid, filigree_maps, finish, gem, interp, invdist, join, lathe,
                      lerp, orient, plate, projector, radial, rigid, ring_points, smoothstep, spike, surface,
                      transform, trim, tube)
from kit.garment import Panel, Wrap
from kit.humanoid import (SIDES, Body, add_skeleton, cuisse, greave, hand, limb_frame, limb_plate, poleyn,
                          rerebrace, sabaton, shell, vambrace)
from kit.motion import Legs, fingers, gait, idle
from kit.rig import R, X, Y, Z

from chars._forge_helpers import (arm_ik, axis_frame, ensure_uv, gorget_lite, lightning_maps, panel_clear, pauldron_lames,
                                  plant_stance, suit_arm_uv, suit_leg_uv, suit_torso_uv, tri_report)
from chars._volt2_parts import arc_plate, cop, etch_maps, fan, texel_uv, zigzag

TITLE = "Volt"
ACCENT = (0.53, 0.73, 1.0)
CLIPS = ("Idle", "Move", "Cast", "Channel")
GAME_TRIS = 62000
BLUE = (0.45, 0.68, 1.0)          # 自发光色（比主题色略饱和）
NAVY = (0.010, 0.020, 0.052)
NAVY_SRGB = (0.100, 0.152, 0.252)  # NAVY 的 sRGB 编码值（给贴图底色用）
SILVER = (0.86, 0.88, 0.92)


def materials(ctx):
    M = ctx.M
    ctx.mat("lacquer", "storm navy lacquer", NAVY, metal=0.35, rough=0.2, coat=1.0, coat_rough=0.03)
    # 注意：贴图按 sRGB 解读，底色要给 sRGB 编码值（NAVY_SRGB ≈ NAVY 的显示值），否则漆面会发黑
    # 漆面下的暗刻卷草纹：高密度细线、低对比沟槽 + 法线凹陷；UV 按世界尺寸重排（texel_uv），每个涡卷约 1 厘米
    ctx.texture("lacquer", filigree_maps(NAVY_SRGB, (0.072, 0.110, 0.190), size=1024, seed=27, density=26, width=1),
                normal_strength=0.30)
    # 头盔专用：细电路刻纹（1 px 走线 + 过孔小环），少量走线透出微光
    ctx.mat("helm", "etched storm helm lacquer", NAVY, metal=0.4, rough=0.18, coat=1.0, coat_rough=0.03)
    ctx.texture("helm", etch_maps(NAVY_SRGB, (0.066, 0.104, 0.182), emit_rgb=BLUE, size=1024, seed=33, cells=16,
                                  glow_share=0.14), emit_strength=0.7, normal_strength=0.35)
    # 四肢导电漆：同款细电路刻纹、发光走线比例更高（远看是细密电纹，不再是大块涂鸦）
    ctx.mat("wired", "conductive navy lacquer", NAVY, metal=0.35, rough=0.22, coat=1.0, coat_rough=0.04)
    ctx.texture("wired", etch_maps(NAVY_SRGB, (0.070, 0.108, 0.186), emit_rgb=BLUE, size=1024, seed=41, cells=10,
                                   glow_share=0.24), emit_strength=1.1, normal_strength=0.4)
    ctx.mat("silver", "bright storm silver", SILVER, metal=1.0, rough=0.16, coat=0.2)
    ctx.texture("silver", filigree_maps(SILVER, (0.56, 0.60, 0.68), size=1024, seed=9, density=22, width=1),
                normal_strength=0.3)
    ctx.mat("suit", "midnight undersuit", (0.010, 0.014, 0.030), metal=0.15, rough=0.55, sheen=0.2,
            sheen_tint=(0.4, 0.6, 1.0))
    ctx.mat("cape", "storm-lit navy cape", (0.012, 0.018, 0.046), rough=0.75, sheen=0.15, sheen_tint=(0.5, 0.7, 1.0),
            spec=0.3)
    ctx.texture("cape", lightning_maps(BLUE, base_rgb=(0.070, 0.098, 0.190), size=1024, seed=17, bolts=11),
                emit_strength=2.6)
    ctx.mat("lining", "electric blue satin lining", (0.030, 0.075, 0.20), rough=0.4, sheen=0.35,
            sheen_tint=(0.6, 0.8, 1.0))
    ctx.mat("visor", "black glass visor", (0.006, 0.008, 0.012), metal=0.1, rough=0.07, coat=1.0, spec=0.8)
    ctx.mat("glow", "arc core glow", (0.7, 0.84, 1.0), emit=BLUE, strength=9.0)
    ctx.mat("inlay", "arc circuit inlay", (0.30, 0.45, 0.70), emit=BLUE, strength=3.6)
    ctx.mat("hem", "arc hem light", (0.25, 0.40, 0.65), emit=BLUE, strength=4.5)
    ctx.mat("blade", "arc-fang crystal", (0.04, 0.07, 0.14), metal=0.6, rough=0.12, coat=1.0)
    ctx.texture("blade", lightning_maps(BLUE, base_rgb=(0.03, 0.06, 0.13), size=512, seed=23, bolts=6, fade=False),
                emit_strength=3.0)
    return M


# ===== 胸甲 =====
G, TH, PL = 0.014, 0.008, 0.010   # 下层胸甲离体距离、甲厚、上胸甲再加高


def pec(B, a, z):
    return 0.014 * B.s * math.exp(-((z - B.z(1.52)) / (0.065 * B.s)) ** 2) * max(0.0, math.cos(a)) ** 2 * \
        (1 - 0.6 * math.exp(-(math.sin(a) / 0.10) ** 2))


def cp(B, x, z, g, back=False):
    """胸甲表面（含胸肌起伏）上方 g 米的点；back=True 取背面。"""
    a = math.asin(clamp(x / (B.torso_r(z)[0] + G), -0.999, 0.999))
    if back:
        a = math.pi - a
    return B.torso_point(a, z, G + pec(B, a, z) + g)


def polyline(B, path, g, back=False, per=6):
    pts = []
    for (x0, z0), (x1, z1) in zip(path, path[1:]):
        for i in range(per):
            t = i / per
            pts.append(cp(B, lerp(x0, x1, t) * B.s, B.z(lerp(z0, z1, t)), g, back))
    pts.append(cp(B, path[-1][0] * B.s, B.z(path[-1][1]), g, back))
    return pts


def build_torso(ctx, B, M):
    s = B.s
    spec = invdist(["Spine", "Chest"])
    shell(ctx, B, f"{ctx.title} cuirass", lambda a: B.z(1.668) - 0.05 * s * max(0.0, math.cos(a)) ** 8,
          lambda a: B.z(1.445) - 0.03 * s * max(0.0, math.cos(a)) ** 6, G, M["lacquer"], spec, thick=TH, nu=72, nv=30,
          sub=0, trims=(M["silver"], 0.0030 * s), shape=lambda a, z: pec(B, a, z))
    # 上胸甲：V 形下缘的独立加高层（四边银滚边），纹章与人字甲都落在这一层上
    pl_top = lambda a: B.z(1.655) - 0.05 * s * max(0.0, math.cos(a)) ** 8
    pl_bot = lambda a: B.z(1.447) + 0.12 * s * abs(math.sin(a)) ** 1.1
    shell(ctx, B, f"{ctx.title} plastron", pl_top, pl_bot, G + PL, M["lacquer"], spec, a0=-1.22, a1=1.22, thick=TH,
          nu=56, nv=22, sub=0, trims=(M["silver"], 0.0034 * s), shape=lambda a, z: pec(B, a, z))
    # 上胸甲下缘外侧的光缝：两道斜向发光线，沿 V 形缘下方 1 厘米走在下层胸甲上
    for sd in (-1, 1):
        pts = []
        for i in range(17):
            a = sd * lerp(0.26, 1.12, i / 16)
            z = pl_bot(a) - 0.011 * s
            pts.append(B.torso_point(a, z, G + pec(B, a, z) + TH + 0.0016 * s))
        ctx.part(trim(f"{ctx.title} plastron seam {sd}", pts, 0.0021 * s, M["inlay"]), spec)
        ctx.part(ellipsoid(f"{ctx.title} seam via {sd}", pts[0], (0.0042 * s,) * 3, [M["glow"]], 8, 5), spec)
    # 分节腹甲：四道环带，每道中部隆起（像一片片叠压的甲片），下缘银边
    for k, (zt, zb, g) in enumerate(((1.452, 1.405, 0.016), (1.412, 1.365, 0.018), (1.372, 1.325, 0.020),
                                     (1.332, 1.288, 0.022))):
        zt_, zb_ = B.z(zt), B.z(zb)
        pt = shell(ctx, B, f"{ctx.title} abdomen {k}", zt_, zb_, g * s, M["lacquer"], spec, nu=56, nv=6,
                   thick=0.006 * s, sub=0,
                   shape=lambda a, z, zt_=zt_, zb_=zb_: 0.0055 * s * math.sin(math.pi * clamp((zt_ - z) / (zt_ - zb_)))
                   ** 0.8 * (0.55 + 0.45 * max(0.0, math.cos(a))))
        ctx.part(trim(f"{ctx.title} abdomen trim {k}", [radial(pt(i / 64, 1.0), 0.007 * s) for i in range(64)],
                      0.0024 * s, M["silver"], closed=True), spec)
    # 胸口：银色人字甲条（双线）+ 闪电纹章（都在上胸甲层上）
    up = PL + TH
    for sd in (-1, 1):
        for off in (0.0, 0.014):
            path = [(sd * 0.168, 1.625 - off), (sd * 0.090, 1.575 - off), (0.0, 1.520 - off)]
            ctx.part(trim(f"{ctx.title} chevron {sd}", polyline(B, path, up + 0.004 * s), 0.0048 * s, M["silver"]),
                     spec)
    bolt = [(0.004, 1.590), (0.030, 1.548), (-0.010, 1.538), (0.020, 1.486), (-0.004, 1.478), (0.002, 1.458)]
    ctx.part(tube(f"{ctx.title} storm sigil", polyline(B, bolt, up + 0.005 * s, per=3), [0.0062 * s] * 16,
                  [M["glow"]], n=8, per=1), spec)
    frame = [(0.0, 1.600), (0.058, 1.528), (0.0, 1.452), (-0.058, 1.528), (0.0, 1.600)]
    ctx.part(trim(f"{ctx.title} sigil frame", polyline(B, frame, up + 0.004 * s), 0.0032 * s, M["silver"]), spec)
    for sd in (-1, 1):
        path = [(sd * 0.02, 1.64), (sd * 0.05, 1.58), (sd * 0.05, 1.49), (sd * 0.11, 1.46)]
        pts = polyline(B, path, TH + 0.0015 * s, back=True)
        ctx.part(trim(f"{ctx.title} back inlay {sd}", pts, 0.0019 * s, M["inlay"]), spec)
    # 腹部中线导电总线：纹章尖端一路下到腰扣
    bus = [B.on_torso(0, B.z(z), lerp(0.037, 0.041, (1.44 - z) / 0.15) * s) for z in [lerp(1.44, 1.29, i / 10)
                                                                                    for i in range(11)]]
    ctx.part(trim(f"{ctx.title} abdomen bus", bus, 0.0022 * s, M["inlay"]), spec)
    gorget_lite(ctx, B, M["silver"], None, layers=((1.645, 1.700, 0.092, 0.072), (1.690, 1.740, 0.074, 0.058)), nu=40)
    # 腰带 + 腰扣 + 两层短腹甲裙
    shell(ctx, B, f"{ctx.title} belt", B.z(1.292), B.z(1.256), 0.030 * s, M["silver"], invdist(["Pelvis", "Spine"]),
          nu=60, nv=4, thick=0.006 * s, sub=0)
    # 腰扣：六边形漆甲扣板 + 银框 + 发光小闪电 + 两侧银铆钉
    pelvis = rigid("Pelvis")
    c = B.on_torso(0, B.z(1.274), 0.046 * s)
    hexo = [(0.0, 0.038), (0.034, 0.021), (0.034, -0.021), (0.0, -0.038), (-0.034, -0.021), (-0.034, 0.021)]
    ctx.part(plate(f"{ctx.title} buckle", [(x * s, z * s) for x, z in hexo], 0.010 * s, [M["lacquer"]], origin=c,
                   xaxis=(1, 0, 0), yaxis=(0, 0, 1), bev=0.0015 * s), pelvis)
    ctx.part(trim(f"{ctx.title} buckle frame", [c + Vector((x * s * 1.02, 0.0058 * s, z * s * 1.02)) for x, z in hexo],
                  0.0030 * s, M["silver"], closed=True), pelvis)
    zb = [(0.006, 0.026), (-0.010, 0.002), (0.008, 0.002), (-0.006, -0.026)]
    ctx.part(tube(f"{ctx.title} buckle bolt", [c + Vector((x * s, 0.0062 * s, z * s)) for x, z in zb],
                  [0.0042 * s, 0.0040 * s, 0.0036 * s, 0.0008 * s], [M["glow"]], n=6, per=1), pelvis)
    for sd in (-1, 1):
        ctx.part(ellipsoid(f"{ctx.title} buckle rivet {sd}", B.on_torso(sd * 0.060 * s, B.z(1.274), 0.037 * s),
                           (0.0050 * s,) * 3, [M["silver"]], 8, 5), pelvis)
    for k, (zt, zb, g) in enumerate(((1.262, 1.190, 0.036), (1.200, 1.128, 0.042))):
        shell(ctx, B, f"{ctx.title} fauld {k}", B.z(zt), lambda a, zb=zb: B.z(zb) - 0.03 * s * max(0.0, math.cos(a)) ** 4,
              g * s, M["lacquer"], rigid("Pelvis"), a0=0.78, a1=TAU - 0.78, nu=44, nv=5, thick=0.006 * s, sub=0,
              trims=(M["silver"], 0.0024 * s))


# ===== 手臂与肩 =====
def fin(ctx, name, origin, xa, ya, outline, mat, spec, depth=0.004):
    ctx.part(plate(name, outline, depth, [mat], origin=origin, xaxis=xa, yaxis=ya, bev=0.001), spec)


def build_arms(ctx, B, M):
    s = B.s
    paul = {}
    for side, label in SIDES:
        # 四片分层肩甲：首片最大、带中脊与后掠尖角，逐片缩小向下叠压；全部漆甲 + 银滚边
        lames = [(0.00, 0.88, 1.00, M["lacquer"], 0.84), (0.62, 1.16, 0.955, M["lacquer"], 0.68),
                 (0.96, 1.46, 0.91, M["lacquer"], 0.52), (1.26, 1.74, 0.865, M["lacquer"], 0.38)]
        lp, sh = pauldron_lames(ctx, B, side, label, lames, radius=0.158, spread=1.34, rise=1.22, tilt=0.30,
                                ridge=0.06, thick=0.008, trim_mat=M["silver"], trim_r=0.0034, nu=36, nv=10,
                                spire=(0.080, -0.42, (0.70, -0.45, 0.55)))
        paul[label] = (lp, sh)
        top = rigid(("Chest", 0.84), (f"UpperArm.{label}", 0.16))
        # 首片中脊：银脊线 + 两侧发光嵌线
        ridge = [lp(0, 0.0, t) for t in [lerp(0.04, 0.96, i / 14) for i in range(15)]]
        ctx.part(trim(f"{ctx.title} pauldron keel {label}",
                      [p + (p - sh).normalized() * 0.012 * s for p in ridge], 0.0036 * s, M["silver"]), top)
        for du in (-0.09, 0.09):
            line = [lp(0, du, t) for t in [lerp(0.10, 0.90, i / 12) for i in range(13)]]
            ctx.part(trim(f"{ctx.title} pauldron inlay {label}", [p + (p - sh).normalized() * 0.010 * s for p in line],
                          0.0018 * s, M["inlay"]), top)
        # 下三片中线：短发光弧 + 两端银铆钉
        for k in (1, 2, 3):
            spec = rigid(("Chest", lames[k][4]), (f"UpperArm.{label}", 1 - lames[k][4]))
            line = [lp(k, u, 0.55) for u in [lerp(-0.55, 0.55, i / 14) for i in range(15)]]
            line = [p + (p - sh).normalized() * 0.010 * s for p in line]
            ctx.part(trim(f"{ctx.title} pauldron line {label}{k}", line, 0.0017 * s, M["inlay"]), spec)
            for u in (-0.72, 0.72):
                p = lp(k, u, 0.55)
                ctx.part(ellipsoid(f"{ctx.title} pauldron rivet {label}{k}", p + (p - sh).normalized() * 0.010 * s,
                                   (0.0048 * s,) * 3, [M["silver"]], 8, 5), spec)
        a = B.arms[label]
        sh_, e, w = a["shoulder"], a["elbow"], a["wrist"]
        ua = rigid(f"UpperArm.{label}")
        fa = rigid(f"Forearm.{label}")
        lim = B.limb * s
        # 上臂：导电漆主甲 + 下缘加一片叠压银边甲（分段）+ 外侧闪电嵌线
        rerebrace(ctx, B, side, label, M["wired"], M["silver"], r=(0.066, 0.056), nu=26, nv=10, sub=0)
        arc_plate(ctx, f"{ctx.title} rerebrace lame {label}", sh_.lerp(e, 0.64), sh_.lerp(e, 0.82),
                  0.066 * lim + 0.009 * s, 0.063 * lim + 0.009 * s, Vector((side, 0, 0.6)), 1.50, M["lacquer"],
                  M["silver"], ua, thick=0.005 * s, bulge=0.003 * s, nu=20, nv=4)
        axis, o, wv = limb_frame(sh_, e, Vector((side, 0, 0.6)))
        ctx.part(trim(f"{ctx.title} rerebrace arc {label}",
                      zigzag(sh_, e, o, wv, lambda v: (lerp(0.066, 0.056, (v - 0.22) / 0.64) * lim + 0.0085 * s),
                             teeth=4, amp=0.16, v0=0.26, v1=0.66), 0.0019 * s, M["inlay"]), ua)
        # 护肘：造型甲杯（中脊 + 铆钉 + 中心线圈）+ 外侧扇片
        bend = (sh_ - e).normalized() + (w - e).normalized()
        back = -bend.normalized() if bend.length > 1e-4 else Vector((0, -1, 0))
        back = (back + Vector((side * 0.55, 0, 0))).normalized()
        cc = e + back * 0.056 * s
        elbow = rigid((f"UpperArm.{label}", 0.5), (f"Forearm.{label}", 0.5))
        cop(ctx, f"{ctx.title} couter {label}", cc, back, sh_ - e, 0.042 * s, 0.052 * s, 0.026 * s, M["lacquer"],
            elbow, M["silver"], M["glow"], keel=0.009 * s, rivets=6, boss=0.013 * s, wrap=0.020 * s)
        out = Vector((side, 0, 0))
        out = (out - back * out.dot(back)).normalized()
        fan(ctx, f"{ctx.title} couter fan {label}", cc + out * 0.036 * s - back * 0.012 * s, back, sh_ - e, 0.044 * s,
            M["lacquer"], M["silver"], elbow, bow=0.008 * s, outward=out, lobes=3)
        # 前臂：导电漆护臂 + 两道银箍分段 + 外侧闪电嵌线 + 疾风鳍
        vambrace(ctx, B, side, label, M["wired"], M["silver"], r=(0.052, 0.056), spur=(M["silver"], 0.05), sub=0)
        fdir = (w - e).normalized()
        a0, a1 = e + fdir * 0.03 * s, w - fdir * 0.012 * s
        axis, o, wv = limb_frame(a0, a1, Vector((side, -0.35, 0.25)))
        for k, t in enumerate((0.36, 0.68)):
            rr = lerp(0.052, 0.056, t) * lim + 0.0045 * s
            ctx.part(trim(f"{ctx.title} vambrace band {label}{k}", ring_points(a0.lerp(a1, t), axis, rr, 26),
                          0.0034 * s, M["silver"], closed=True), fa)
        ctx.part(trim(f"{ctx.title} vambrace arc {label}",
                      zigzag(a0, a1, o, wv, lambda v: lerp(0.052, 0.056, v) * lim + 0.0040 * s, teeth=5, amp=0.20,
                             v0=0.06, v1=0.94), 0.0018 * s, M["inlay"]), fa)
        base = e.lerp(w, 0.62) + o * 0.058 * s
        for k, (L, h) in enumerate(((0.15, 0.040), (0.11, 0.028))):
            outline = [(-0.03 * s, 0.0), (L * s, 0.004 * s), ((L + 0.03) * s, h * s), (0.02 * s, 0.014 * s)]
            fin(ctx, f"{ctx.title} arm fin {label}{k}", base - fdir * 0.035 * k * s, -fdir, o, outline, M["silver"], fa)
    return paul


# ===== 腿 =====
def build_legs(ctx, B, M):
    s = B.s
    for side, label in SIDES:
        L = B.legs[label]
        hip, knee, ankle = L["hip"], L["knee"], L["ankle"]
        lim = B.limb * s
        thigh, shin = rigid(f"Thigh.{label}"), rigid(f"Shin.{label}")
        CU, GR = (0.104, 0.086), (0.074, 0.056)
        cuisse(ctx, B, side, label, M["wired"], M["silver"], r=CU, nu=26, nv=12, sub=0)
        greave(ctx, B, side, label, M["wired"], M["silver"], r=GR, nv=14, sub=0)
        sabaton(ctx, B, side, label, M["silver"], M["silver"], width=0.054, height=0.060, toe_mat=M["lacquer"])
        # 腿甲外表面半径（含 kit 的隆起 / 中脊 / 甲厚），叠片按它再外扩，保证不埋进底甲
        def cu_r(v):
            vc = clamp((v - 0.10) / 0.78)
            return CU[0] * lim + (CU[1] - CU[0]) * lim * vc + (0.006 * math.sin(vc * math.pi) + 0.006 + 0.005) * s

        def gr_r(v):
            vg = clamp((v - 0.10) / 0.83)
            return GR[0] * lim + (GR[1] - GR[0]) * lim * vg + (0.010 * math.sin(vg * math.pi) + 0.006 + 0.005) * s

        def shingle(name, a, b, v0, v1, rfn, gap, out, arc, spec, ridge, nu, nv, **kw):
            ra, rb, rm = rfn(v0) + gap, rfn(v1) + gap, rfn((v0 + v1) / 2) + gap
            arc_plate(ctx, name, a.lerp(b, v0), a.lerp(b, v1), ra, rb, out, arc, M["lacquer"], M["silver"], spec,
                      thick=0.005 * s, ridge=ridge, bulge=max(0.0, rm - (ra + rb) / 2), nu=nu, nv=nv, **kw)
        # 膝上 / 膝下关节窄叠片：衔接大腿甲、护膝、胫甲（窄而贴，甲杯压在它们外面）
        shingle(f"{ctx.title} knee lame top {label}", hip, knee, 0.86, 0.95, cu_r, 0.002 * s,
                Vector((side * 0.3, 1, 0)), 1.05, thigh, 0.0, 18, 3)
        shingle(f"{ctx.title} knee lame low {label}", knee, ankle, 0.04, 0.11, gr_r, 0.003 * s,
                Vector((side * 0.3, 1, 0)), 1.00, shin, 0.0, 18, 3)
        # 护膝：造型甲杯（上下中脊 + 铆钉 + 中心线圈）+ 外侧四瓣扇片；两侧向后包住膝盖
        kf = Vector((side * 0.10, 1, 0.05)).normalized()
        kc = knee + kf * 0.090 * s + Vector((0, 0, 0.004 * s))
        kspec = rigid((f"Thigh.{label}", 0.5), (f"Shin.{label}", 0.5))
        cop(ctx, f"{ctx.title} poleyn {label}", kc, kf, hip - knee, 0.066 * s, 0.072 * s, 0.036 * s, M["lacquer"],
            kspec, M["silver"], M["glow"], keel=0.013 * s, rivets=8, boss=0.018 * s, wrap=0.034 * s)
        out = Vector((side, 0, 0))
        fan(ctx, f"{ctx.title} poleyn fan {label}", knee + out * 0.104 * s + Vector((0, 0.030 * s, 0.004 * s)),
            Vector((0, -1, 0.08)), Vector((0, 0, 1)), 0.064 * s, M["lacquer"], M["silver"], kspec, bow=0.012 * s,
            outward=out, lobes=4)
        # 胫甲前侧三段叠压甲片（下段压上段），每段四边银滚边，中脊隆起、向下收窄
        for k, (v0, v1) in enumerate(((0.16, 0.43), (0.40, 0.67), (0.64, 0.91))):
            shingle(f"{ctx.title} shin plate {label}{k}", knee, ankle, v0, v1, gr_r, (0.004 + 0.004 * k) * s,
                    Vector((side * 0.12, 1, 0)), 0.80, shin, 0.006 * s, 14, 5, arc1=0.66)
        # 大腿前侧中脊甲片：上宽下窄，下缘中间收成尖角指向护膝
        shingle(f"{ctx.title} thigh plate {label}", hip, knee, 0.20, 0.70, cu_r, 0.005 * s,
                Vector((side * 0.30, 1, 0)), 0.70, thigh, 0.006 * s, 14, 7, arc1=0.46, point=0.16)
        # 腿外侧闪电嵌线（髋 → 膝，膝 → 踝）
        for (a0, a1, spec, rr0, rr1, v0, v1) in ((hip, knee, thigh, CU[0], CU[1], 0.12, 0.80),
                                                 (knee, ankle, shin, GR[0], GR[1], 0.16, 0.90)):
            axis, o, wv = limb_frame(a0, a1, Vector((side, 0.35, 0)))
            pts = zigzag(a0, a1, o, wv, lambda v, rr0=rr0, rr1=rr1: (lerp(rr0, rr1, v) * B.limb +
                                                                    0.010 * math.sin(v * math.pi) + 0.0085) * s,
                         teeth=5, amp=0.13, v0=v0, v1=v1)
            ctx.part(trim(f"{ctx.title} leg arc {label}", pts, 0.0020 * s, M["inlay"]), spec)
            ctx.part(ellipsoid(f"{ctx.title} leg via {label}", pts[-1], (0.0045 * s,) * 3, [M["glow"]], 8, 5), spec)
        # 大腿外侧挂甲
        limb_plate(ctx, f"{ctx.title} tasset {label}", L["hip"] + Vector((0, 0, 0.09 * s)), L["hip"].lerp(knee, 0.30),
                   0.118 * s, 0.112 * s, M["lacquer"], rigid(f"Thigh.{label}"), Vector((side, 0.25, 0)), arc=0.9,
                   thick=0.006 * s, trim_mat=M["silver"], trim_r=0.0024 * s, rims=(1,), nu=20, nv=8, sub=0)
        # 踝侧后掠疾风翼（两片）
        xa = Vector((0, -1, 0.45)).normalized()
        ya = Vector((0, 0.3, 1.0)).normalized()
        origin = ankle + Vector((side * 0.060 * s, 0.005 * s, 0.030 * s))
        outline = [(0.0, 0.0), (0.12 * s, 0.010 * s), (0.17 * s, 0.050 * s), (0.07 * s, 0.036 * s),
                   (0.11 * s, 0.078 * s), (0.02 * s, 0.050 * s)]
        fin(ctx, f"{ctx.title} ankle wing {label}", origin, xa, ya, outline, M["silver"], rigid(f"Shin.{label}"))
        ctx.part(gem(f"{ctx.title} ankle gem {label}", origin + Vector((side * 0.004 * s, 0, 0.012 * s)), 0.008 * s,
                     M["glow"], (0.6, 1, 1)), rigid(f"Shin.{label}"))


# ===== 高盔 =====
def build_helm(ctx, B, M):
    """风暴高盔：盔体 + 眉脊（下缘外挑）+ V 形眼缝 + 四段面甲（中缝发光）+ 两侧后掠闪电鳍 + 避雷针底座。"""
    s = B.s
    hc = Vector((0, 0.012 * s, B.z(1.885)))
    rx, ry, rz = 0.103 * s, 0.120 * s, 0.170 * s
    prof = [(0.0, (0.00, 0.172)), (0.10, (0.42, 0.165)), (0.24, (0.76, 0.128)), (0.40, (0.95, 0.064)),
            (0.52, (1.00, 0.020)), (0.66, (0.99, -0.030)), (0.82, (0.92, -0.085)), (1.0, (0.96, -0.135))]
    head = rigid("Head")
    H = M["helm"]

    def eye(a):
        """眼缝中线的 v：正中最低、向两侧上挑。"""
        return 0.548 - 0.032 * min(1.0, abs(a) / 0.80) ** 1.3

    def hpa(a, v, slit=True):
        r, dz = interp(prof, v)
        front = max(0.0, math.cos(a))
        back = max(0.0, -math.cos(a))
        x = rx * r * math.sin(a)
        y = ry * r * math.cos(a)
        z = hc.z + dz * s
        y -= 0.040 * s * back * (1 - v) ** 2                       # 盔顶后掠
        y += 0.016 * s * math.exp(-(x / (0.016 * s)) ** 2) * front ** 2 * smoothstep(0.2, 0.9, v)   # 面部龙骨
        d3 = Vector((x, y, 0)).normalized() if r > 1e-4 else Vector((0, 0, 0))
        off = 0.010 * s * smoothstep(0.86, 1.0, v)
        if slit:                                                    # 眼缝凹槽
            off -= 0.009 * s * math.exp(-((v - eye(a)) / 0.014) ** 2) * smoothstep(0.30, 0.62, front)
        return Vector((x, y + hc.y, z)) + d3 * off

    def nrm(p):
        return Vector((p.x / rx ** 2, (p.y - hc.y) / ry ** 2, (p.z - hc.z) / rz ** 2)).normalized()

    helm = surface(f"{ctx.title} helm", lambda u, v: hpa(u * TAU, v), 96, 54, [H])
    orient(helm, lambda c: hc)
    helm = finish(helm, 0.004 * s, -1, 0)
    ctx.part(helm, head)

    def patch(name, a0, a1, vt, vb, lift, nu, nv, mat=H, thick=0.004 * s, tr=0.0030 * s, edges=(1, 1, 1, 1)):
        """贴盔体的加高甲片：a0→a1 方位、vt(a)→vb(a) 高度参数，lift(a, t) 沿盔面法向外扩；edges=(上, 下, 左, 右) 银滚边。"""
        def pt(uu, t, extra=0.0):
            a = lerp(a0, a1, uu)
            p = hpa(a, lerp(vt(a), vb(a), t), slit=False)
            return p + nrm(p) * (lift(a, t) + extra)
        obj = surface(name, lambda uu, t: pt(uu, t), nu, nv, [mat])
        orient(obj, lambda c: hc)
        ctx.part(finish(obj, thick, 1, 0), head)
        e = thick + tr * 0.5
        for on, (fixed, param) in zip(edges, (("t", 0.0), ("t", 1.0), ("u", 0.0), ("u", 1.0))):
            if not on:
                continue
            pts = ([pt(i / (nu + 4), param, e) for i in range(nu + 5)] if fixed == "t" else
                   [pt(param, j / 12, e) for j in range(13)])
            ctx.part(trim(f"{name} trim", pts, tr, M["silver"]), head)
        return pt

    # 眉脊：从两侧太阳穴绕到眉心，截面是向下外挑的楔形（下缘最厚），在眼缝上方投下阴影
    BA = 1.30
    brow = patch(f"{ctx.title} brow", -BA, BA, lambda a: eye(a) - 0.090, lambda a: eye(a) - 0.030,
                 lambda a, t: s * (0.003 + 0.013 * t ** 0.8) * (1 - (abs(a) / BA) ** 4 * 0.85), 64, 6,
                 tr=0.0034 * s)
    # 盔顶分瓣肋：四道窄加高肋条从眉脊 / 盔沿向上收拢到避雷针座，把子弹形圆顶分成几瓣
    for ac in (0.62, -0.62, 2.25, -2.25):
        patch(f"{ctx.title} dome rib {ac:+.2f}", ac - 0.055, ac + 0.055, lambda a: 0.07,
              lambda a: (eye(a) - 0.092) if abs(a) < 1.5 else 0.46, lambda a, t: 0.0028 * s, 4, 16, tr=0.0020 * s,
              edges=(0, 0, 1, 1))
    # 眼缝：V 形发光细管嵌在凹槽里
    slit = [hpa(a, eye(a)) + nrm(hpa(a, eye(a))) * 0.0015 * s for a in [lerp(-0.86, 0.86, i / 30) for i in range(31)]]
    ctx.part(tube(f"{ctx.title} visor slit", slit, [0.0010 * s] + [0.0044 * s] * 29 + [0.0010 * s], [M["glow"]], n=8,
                  per=1), head)
    # 面甲四段：中缝两片 + 左右颊甲（颊甲下缘向后收，上缘在眼缝尽头接到眉脊）
    top = lambda a: eye(a) + 0.030 - 0.058 * smoothstep(0.86, 1.18, abs(a))
    for sd in (-1, 1):
        a0, a1 = (0.035, 0.33) if sd > 0 else (-0.33, -0.035)
        mp = patch(f"{ctx.title} face plate {sd}", a0, a1, top, lambda a: 0.965, lambda a, t: 0.0055 * s, 10, 12,
                   tr=0.0022 * s)
        for k, t in enumerate((0.42, 0.58, 0.74)):                 # 呼吸格栅：三道银肋
            ctx.part(trim(f"{ctx.title} vent {sd}{k}", [mp(u, t, 0.0050 * s) for u in (0.22, 0.45, 0.68, 0.88)],
                          0.0017 * s, M["silver"]), head)
        a0, a1 = (0.37, 1.45) if sd > 0 else (-1.45, -0.37)
        patch(f"{ctx.title} cheek {sd}", a0, a1, top, lambda a: 0.99 - 0.10 * smoothstep(0.85, 1.45, abs(a)),
              lambda a, t: s * (0.0060 + 0.0025 * math.sin(math.pi * t)), 24, 12, tr=0.0024 * s)
    stem = [hpa(0.0, v, slit=False) + nrm(hpa(0.0, v, slit=False)) * 0.0020 * s for v in
            [lerp(eye(0.0) + 0.012, 0.93, i / 12) for i in range(13)]]
    ctx.part(tube(f"{ctx.title} visor stem", stem, [0.0036 * s] * 12 + [0.0010 * s], [M["glow"]], n=8, per=1), head)
    # 后半圈眉线与盔沿银边
    band = [radial(hpa(a, 0.46), 0.003 * s, hc.y) for a in [lerp(BA - 0.02, TAU - BA + 0.02, i / 60) for i in range(61)]]
    ctx.part(trim(f"{ctx.title} brow band", band, 0.0034 * s, M["silver"]), head)
    rim = [radial(hpa(i / 96 * TAU, 1.0), 0.003 * s, hc.y) for i in range(96)]
    ctx.part(trim(f"{ctx.title} helm rim", rim, 0.0036 * s, M["silver"], closed=True), head)
    # 护颈短叠片（只在后半圈，略外翻）
    def nape(u, t):
        a = lerp(math.pi - 1.0, math.pi + 1.0, u)
        p = hpa(a, 1.0)
        d = Vector((p.x, p.y - hc.y, 0)).normalized()
        return p + d * (0.006 + 0.012 * t) * s - Vector((0, 0, 0.024 * s * t))
    ctx.part(finish(orient(surface(f"{ctx.title} nape", nape, 30, 4, [H]), lambda c: Vector((0, hc.y, c.z))),
                    0.004 * s, 1, 0), head)
    ctx.part(trim(f"{ctx.title} nape trim", [nape(i / 30, 1.0) + Vector((0, 0, -0.002 * s)) for i in range(31)],
                  0.0028 * s, M["silver"]), head)
    # 后掠鳍冠：自眉心越过盔顶直到后颈，后段更高
    path = [hpa(0.0, v) for v in [0.46 - i / 30 * 0.46 for i in range(31)]]
    path += [hpa(math.pi, v) for v in [i / 30 * 0.80 for i in range(31)]][1:]

    def crest_at(t):
        f = t * (len(path) - 1)
        i = min(len(path) - 2, int(f))
        return path[i].lerp(path[i + 1], f - i)

    def crest_pt(u, v):
        p = crest_at(u)
        n = (p - hc).normalized()
        h = 0.046 * s * math.sin(math.pi * u) ** 0.7 * lerp(0.45, 1.30, u)
        return p + n * (h * v - 0.004 * s)
    ctx.part(finish(surface(f"{ctx.title} crest", crest_pt, 60, 6, [H]), 0.006 * s, 0, 0), head)
    ctx.part(trim(f"{ctx.title} crest edge", [crest_pt(i / 60, 1.0) for i in range(61)], 0.0030 * s, M["silver"]), head)
    for sd in (-1, 1):
        line = [crest_pt(i / 40, 0.55) + Vector((sd * 0.0034 * s, 0, 0)) for i in range(5, 37)]
        ctx.part(trim(f"{ctx.title} crest line {sd}", line, 0.0014 * s, M["inlay"]), head)
    # 避雷针底座：银色车削绝缘座（台阶 + 发光环）+ 四根斜撑落到盔顶
    rod0 = hpa(0.0, 0.0) + Vector((0, -0.012 * s, -0.004 * s))
    rod1 = rod0 + Vector((0, -0.030 * s, 0.235 * s))
    F = axis_frame(rod0, rod1 - rod0)
    sock = lathe(f"{ctx.title} rod socket", [(r * s, z * s) for r, z in
                                             ((0.008, 0.060), (0.014, 0.056), (0.014, 0.044), (0.021, 0.040),
                                              (0.021, 0.029), (0.030, 0.023), (0.037, 0.010), (0.041, -0.002),
                                              (0.035, -0.022))], [M["silver"]], segments=24)
    transform(sock, F)
    ctx.part(sock, head)
    L = lambda x, y, z: F @ Vector((x * s, y * s, z * s))
    ctx.part(trim(f"{ctx.title} socket glow", [L(math.cos(t) * 0.034, math.sin(t) * 0.034, 0.017)
                                               for t in [i / 22 * TAU for i in range(22)]], 0.0030 * s, M["glow"],
                  closed=True), head)
    ctx.part(trim(f"{ctx.title} socket collar", [L(math.cos(t) * 0.0225, math.sin(t) * 0.0225, 0.034)
                                                 for t in [i / 18 * TAU for i in range(18)]], 0.0026 * s, M["glow"],
                  closed=True), head)
    for th in (0.8, math.pi - 0.8, math.pi + 0.8, TAU - 0.8):
        foot = hpa(th, 0.17)
        foot = foot + nrm(foot) * 0.002 * s
        ctx.part(tube(f"{ctx.title} socket strut", [L(math.sin(th) * 0.028, math.cos(th) * 0.028, 0.020), foot],
                      [0.0060 * s, 0.0038 * s], [M["silver"]], n=6, per=1), head)
    ctx.part(tube(f"{ctx.title} lightning rod", [rod0 + (rod1 - rod0) * 0.2, rod1], [0.0060 * s, 0.0028 * s],
                  [M["silver"]], n=10, per=1), head)
    for k, (t, r) in enumerate(((0.36, 0.018), (0.56, 0.015), (0.76, 0.011))):
        c = rod0.lerp(rod1, t)
        ctx.part(trim(f"{ctx.title} rod ring {k}", ring_points(c, rod1 - rod0, r * s, 18), 0.0034 * s, M["glow"],
                      closed=True), head)
    ctx.part(ellipsoid(f"{ctx.title} rod orb", rod1 + Vector((0, -0.001 * s, 0.010 * s)), (0.011 * s,) * 3, [M["glow"]],
                       14, 10), head)
    ctx.part(spike(f"{ctx.title} rod tip", rod1 + Vector((0, -0.001 * s, 0.018 * s)), rod1 + Vector((0, -0.004 * s, 0.060 * s)),
                   0.0035 * s, [M["silver"]], sides=6), head)
    # 两侧后掠闪电鳍（主鳍 + 副鳍）：漆甲鳍面 + 银滚边 + 中线发光嵌线 + 发光尖端
    FIN = [(-0.012, -0.022), (0.070, -0.016), (0.150, -0.002), (0.250, 0.036), (0.165, 0.028), (0.182, 0.054),
           (0.100, 0.034), (0.108, 0.058), (0.030, 0.034), (-0.012, 0.026)]
    MID = [(0.004, 0.004), (0.080, 0.008), (0.150, 0.016), (0.215, 0.030)]
    for sd, label in SIDES:
        for k, (a_root, v_root, xa, scale) in enumerate(((1.40, 0.43, (0.22, -0.88, 0.50), 1.0),
                                                         (1.55, 0.56, (0.25, -0.92, 0.28), 0.62))):
            o = hpa(sd * a_root, v_root)
            o = o + nrm(o) * 0.004 * s
            xa = Vector((sd * xa[0], xa[1], xa[2])).normalized()
            ya = Vector((0, 0.45, 1.0))
            ya = (ya - xa * ya.dot(xa)).normalized()
            na = xa.cross(ya)
            face = 1.0 if na.x * sd > 0 else -1.0
            bend = 0.38 / scale

            def P(x, y, n=0.0, o=o, xa=xa, ya=ya, na=na, face=face, bend=bend, scale=scale):
                x, y = x * scale * s, y * scale * s
                return o + xa * x + ya * y + na * (face * bend * x * x + face * n * s)
            outline = [(x * scale * s, y * scale * s) for x, y in FIN]
            ctx.part(plate(f"{ctx.title} helm fin {label}{k}", outline, 0.007 * s * (0.8 + 0.2 * scale), [H], origin=o,
                           xaxis=xa, yaxis=ya, bulge=lambda x, y, f=face, b=bend: f * b * x * x, bev=0.0012 * s),
                     head)
            ctx.part(trim(f"{ctx.title} helm fin edge {label}{k}", [P(x, y, 0.0036) for x, y in FIN], 0.0024 * s,
                          M["silver"], closed=True), head)
            ctx.part(trim(f"{ctx.title} helm fin inlay {label}{k}", [P(x, y, 0.0040) for x, y in MID], 0.0020 * s,
                          M["inlay"], per=4), head)
            ctx.part(spike(f"{ctx.title} helm fin tip {label}{k}", P(0.232, 0.033), P(0.290, 0.047), 0.0050 * s * scale,
                           [M["glow"]], sides=6), head)
        # 鳍根线圈耳盘
        pr = projector(helm, (-sd, 0, 0))
        ec = pr(Vector((sd * 0.5, hc.y - 0.012 * s, hc.z + 0.020 * s)), 0.004 * s)
        ctx.part(trim(f"{ctx.title} ear coil {label}", ring_points(ec, (sd, 0, 0), 0.021 * s, 20), 0.0038 * s,
                      M["silver"], closed=True), head)
        ctx.part(trim(f"{ctx.title} ear ring {label}", ring_points(ec + Vector((sd * 0.003 * s, 0, 0)), (sd, 0, 0),
                                                                    0.011 * s, 16), 0.0030 * s, M["glow"], closed=True),
                 head)
    return hc


# ===== 特斯拉线圈塔 =====
def coil_frame(B, sd):
    base = Vector((sd * 0.140, -0.130, 1.600)) * B.s
    axis = Vector((sd * 0.30, -0.28, 1.0)).normalized()
    return base, axis, axis_frame(base, axis)


def build_coils(ctx, B, M, paul):
    """双肩后方的特斯拉线圈：固定插座（Chest）+ 可动线圈体（Coil.L/R：桅杆、叠环、环形顶载、放电弧）。
    插座外套一圈漆甲底盘，两条扁平甲带把底盘接到肩甲首片上，线圈和肩甲连成一体。"""
    s = B.s
    chest = rigid("Chest")
    coils = {}
    for sd, label in SIDES:
        base, axis, F = coil_frame(B, sd)
        L = lambda x, y, z: F @ Vector((x * s, y * s, z * s))
        # 底盘：车削碟形漆甲座（银边 + 一圈铆钉），与肩甲首片的后缘相接
        dish = lathe(f"{ctx.title} coil mount {label}", [(0.040 * s, 0.018 * s), (0.056 * s, 0.012 * s),
                                                         (0.074 * s, -0.004 * s), (0.080 * s, -0.020 * s),
                                                         (0.070 * s, -0.036 * s)], [M["lacquer"]], segments=28)
        transform(dish, F)
        ctx.part(finish(dish, 0.004 * s, 1, 0), chest)
        ctx.part(trim(f"{ctx.title} coil mount rim {label}", [L(math.cos(t) * 0.081, math.sin(t) * 0.081, -0.021)
                                                              for t in [i / 32 * TAU for i in range(32)]],
                      0.0034 * s, M["silver"], closed=True), chest)
        for i in range(8):
            t = i / 8 * TAU + 0.2
            ctx.part(ellipsoid(f"{ctx.title} coil mount rivet {label}", L(math.cos(t) * 0.064, math.sin(t) * 0.064, 0.010),
                               (0.0042 * s,) * 3, [M["silver"]], 8, 5), chest)
        lp, sh = paul[label]
        strap_spec = rigid(("Chest", 0.84), (f"UpperArm.{label}", 0.16))
        for k, u in enumerate((-0.30, -0.62)):
            end = lp(0, u, 0.30)
            end = end + (end - sh).normalized() * 0.006 * s
            t0 = (k * 1.3 + 0.35) * (1 if sd > 0 else -1)
            start = L(math.cos(t0) * 0.050, math.sin(t0) * 0.050, 0.004)
            mid = start.lerp(end, 0.5) + axis * 0.020 * s
            ctx.part(tube(f"{ctx.title} coil strap {label}{k}", [start, mid, end], [0.011 * s, 0.010 * s, 0.009 * s],
                          [M["lacquer"]], n=8, fx=1.0, fy=0.35, up=tuple(axis), per=4), strap_spec)
            ctx.part(trim(f"{ctx.title} coil cable {label}{k}", [start + axis * 0.004 * s, mid + axis * 0.005 * s,
                                                                 end + axis * 0.002 * s], 0.0020 * s, M["inlay"],
                          per=4), strap_spec)
        sock = lathe(f"{ctx.title} coil socket {label}", [(0.024 * s, 0.070 * s), (0.034 * s, 0.062 * s),
                                                          (0.036 * s, 0.020 * s), (0.046 * s, -0.010 * s),
                                                          (0.040 * s, -0.050 * s), (0.030 * s, -0.110 * s)],
                     [M["silver"]], segments=22)
        transform(sock, F)
        ctx.part(sock, chest)
        ctx.part(trim(f"{ctx.title} socket ring {label}", [L(math.cos(t) * 0.040, math.sin(t) * 0.040, 0.0)
                                                           for t in [i / 20 * TAU for i in range(20)]],
                      0.0040 * s, M["glow"], closed=True), chest)
        ctx.part(tube(f"{ctx.title} coil core {label}", [L(0, 0, -0.04), L(0, 0, 0.13)], [0.010 * s, 0.010 * s],
                      [M["glow"]], n=8, per=1), chest)
        spec = rigid(f"Coil.{label}")
        ctx.part(tube(f"{ctx.title} coil mast {label}", [L(0, 0, 0.05), L(0, 0, 0.42)], [0.013 * s, 0.009 * s],
                      [M["inlay"]], n=10, per=1), spec)
        for i in range(6):
            z = 0.09 + i * 0.052
            rr = 0.060 - i * 0.0062
            mat, tr = (M["silver"], 0.0058) if i % 2 == 0 else (M["glow"], 0.0042)
            ctx.part(trim(f"{ctx.title} coil ring {label}{i}", [L(math.cos(t) * rr, math.sin(t) * rr, z)
                                                                for t in [j / 28 * TAU for j in range(28)]],
                          tr * s, mat, closed=True), spec)
            for j in range(3):
                t = j / 3 * TAU + i * 0.7
                ctx.part(tube(f"{ctx.title} coil spoke {label}", [L(math.cos(t) * 0.014, math.sin(t) * 0.014, z),
                                                                  L(math.cos(t) * (rr - 0.004), math.sin(t) * (rr - 0.004), z)],
                              [0.0024 * s] * 2, [M["silver"]], n=5, per=1), spec)
        # 次级绕组：银丝紧密螺旋缠在发光芯柱外，匝间透出蓝光
        turns = 20
        helix = [L(math.cos(t) * 0.019, math.sin(t) * 0.019, 0.07 + 0.31 * t / (turns * TAU))
                 for t in [i / 9 * TAU for i in range(turns * 9 + 1)]]
        ctx.part(trim(f"{ctx.title} coil winding {label}", helix, 0.0024 * s, M["silver"], n=5), spec)
        top = 0.44
        ctx.part(trim(f"{ctx.title} coil toroid {label}", [L(math.cos(t) * 0.044, math.sin(t) * 0.044, top)
                                                           for t in [j / 30 * TAU for j in range(30)]],
                      0.0140 * s, M["silver"], closed=True, n=10), spec)
        ctx.part(ellipsoid(f"{ctx.title} coil orb {label}", L(0, 0, top + 0.004), (0.024 * s,) * 3, [M["glow"]], 16, 10),
                 spec)
        ctx.part(spike(f"{ctx.title} coil tip {label}", L(0, 0, top + 0.02), L(0, 0, top + 0.10), 0.006 * s,
                       [M["silver"]], sides=6), spec)
        # 放电弧：自顶载向外的折线光丝
        for k in range(3):
            t0 = k / 3 * TAU + 0.5
            pts = []
            for i in range(6):
                rr = 0.058 + i * 0.012
                jit = 0.35 * (1 if i % 2 else -1)
                pts.append(L(math.cos(t0 + jit * 0.3) * rr, math.sin(t0 + jit * 0.3) * rr, top + 0.004 + 0.012 * i * (1 if k else -0.6)))
            ctx.part(tube(f"{ctx.title} coil arc {label}{k}", pts, [0.0030 * s, 0.0026 * s, 0.0022 * s, 0.0018 * s,
                                                                    0.0014 * s, 0.0005 * s], [M["glow"]], n=5, per=1),
                     spec)
        coils[label] = (L(0, 0, 0.05), L(0, 0, 0.46), axis)
    return coils


# ===== 展示页环绕武器 =====
FANG = [(0.0, -0.018), (0.10, -0.022), (0.20, -0.018), (0.30, -0.004), (0.38, 0.018), (0.44, 0.048), (0.475, 0.072),
        (0.43, 0.066), (0.36, 0.047), (0.28, 0.037), (0.18, 0.034), (0.08, 0.030), (0.0, 0.024)]


def build_blade(ctx, B, M):
    """展示页环绕的弧牙刃（只进展示版；局部原点在刃中部，刃尖朝 +Y）：晶体刃身 + 发光刃口 + 银色护手与小线圈。"""
    s = B.s
    center = Vector((0.66 * s, 0.10 * s, 1.30 * s))
    o = center - Vector((0, 0.14 * s, 0))
    xa, ya = Vector((0, 1, 0)), Vector((1, 0, 0))
    P = lambda x, y, n=0.0: o + xa * x * s + ya * y * s + Vector((0, 0, -1)) * n * s
    objs = [plate(f"{ctx.title} fang blade", [(x * s, y * s) for x, y in FANG], 0.012 * s, [M["blade"]], origin=o,
                  xaxis=xa, yaxis=ya, bev=0.002 * s)]
    edge = [P(x, y + 0.003) for x, y in FANG[6:]]
    objs.append(tube(f"{ctx.title} fang edge", edge, [0.0022 * s] * len(edge), [M["hem"]], n=6, per=4))
    objs.append(tube(f"{ctx.title} fang guard", [P(-0.010, -0.050), P(-0.010, 0.0), P(-0.010, 0.056)],
                     [0.006 * s, 0.011 * s, 0.006 * s], [M["silver"]], n=8, fx=1.0, fy=0.6, up=(0, 0, 1)))
    objs.append(trim(f"{ctx.title} fang coil", ring_points(P(-0.010, 0.003), (0, 1, 0), 0.020 * s, 18), 0.0032 * s,
                     M["glow"], closed=True))
    objs.append(tube(f"{ctx.title} fang grip", [P(-0.015, 0.003), P(-0.13, 0.0)], [0.011 * s, 0.010 * s],
                     [M["lacquer"]], n=10, per=1))
    for i in range(4):
        objs.append(trim(f"{ctx.title} fang wrap", ring_points(P(-0.035 - i * 0.026, 0.002), (0, 1, 0), 0.0115 * s, 12),
                         0.0022 * s, M["silver"], closed=True))
    objs.append(gem(f"{ctx.title} fang pommel", P(-0.140, 0.0), 0.012 * s, M["glow"], (1, 1.2, 1)))
    blade = join(objs, f"{ctx.ID}_BLADE", center)
    # 只转节点不转网格：审图里刃尖朝上悬在身侧，网页端环绕实例只取网格（刃尖仍是局部 +Y）
    blade.rotation_euler = (math.radians(90), 0, 0)
    ctx.hidden.append(blade)


# ===== 布料 =====
def cloth(B):
    s = B.s
    capes = []
    for label, a0, a1, seed in (("CapeL", math.pi + 0.13, math.pi + 1.34, 1.7), ("CapeR", math.pi - 1.34, math.pi - 0.13, 3.1)):
        capes.append(Wrap(label, "Chest", a0, a1,
                          top=lambda u, lab=label: B.z(1.660) - 0.030 * s * (u if lab == "CapeL" else 1 - u) ** 1.5,
                          bottom=B.z(0.76), r_top=(0.228 * s, 0.132 * s), r_bot=(0.44 * s, 0.34 * s), K=3,
                          joints=(0, 0.16, 0.34, 0.52, 0.74, 1.0), cy=-0.02 * s, flow=0.10 * s,
                          folds=(5.0, 0.005 * s, 0.030 * s), seed=seed, tails=3, tail_len=(0.07 * s, 0.035 * s),
                          curl=(0.02 * s, 0.008 * s), flare_exp=1.1))
    front = Panel("TabardF", "Pelvis", B.z(1.258), B.z(0.80), [(0, 0.19 * s), (0.6, 0.17 * s), (1.0, 0.12 * s)],
                  [(0, 0.108 * s), (0.1, 0.128 * s), (0.5, 0.142 * s), (1.0, 0.150 * s)], side=1, point=0.25)
    return capes, front


def build(ctx):
    M = materials(ctx)
    # limb 1.06：四肢加粗，和加宽的肩甲 / 分层胸甲协调，不再像细管
    B = Body(height=2.0, shoulder=0.205, bulk=0.97, chest=1.04, waist=0.90, hips=0.98, limb=1.06, arm_out=0.60)
    s = B.s
    suit_torso_uv(ctx, B, M["suit"])
    for side, label in SIDES:
        suit_arm_uv(ctx, B, side, label, M["suit"])
        suit_leg_uv(ctx, B, side, label, M["suit"])
        hand(ctx, B, side, label, M["silver"], glow=M["glow"], scale=1.18)
    build_torso(ctx, B, M)
    paul = build_arms(ctx, B, M)
    build_legs(ctx, B, M)
    hc = build_helm(ctx, B, M)
    coils = build_coils(ctx, B, M, paul)
    build_blade(ctx, B, M)
    capes, front = cloth(B)
    for g, name in zip(capes, ("left", "right")):
        g.build(ctx, [M["cape"], M["lining"]], f"{ctx.title} cape {name}", nu=46, nv=42, uv_scale=0.7,
                hem=(M["hem"], 0.0026 * s), edges=(M["silver"], 0.0030 * s))
    front.build(ctx, [M["cape"], M["lining"]], f"{ctx.title} tabard", nu=14, nv=36, edges=(M["silver"], 0.0028 * s),
                spine=(M["inlay"], 0.0018 * s))
    # 甲面贴图按世界尺寸重复：漆甲 / 导电漆 / 银件每 tile 米一次（kit 曲面 UV 是整块 0..1，会把雕花放大成大圈）
    tiles = {M["lacquer"].name: 0.26, M["helm"].name: 0.15, M["wired"].name: 0.24, M["silver"].name: 0.30}
    for obj, _ in ctx.parts:
        mat = obj.data.materials[0].name if obj.data.materials else None
        if mat in tiles and obj.data.uv_layers:
            texel_uv(obj, tiles[mat])
    ensure_uv(ctx)
    tri_report(ctx)
    return {"B": B, "capes": capes, "front": front, "hc": hc, "coils": coils}


def skeleton(rig, st):
    B = st["B"]
    add_skeleton(rig, B)
    for label, (h, t, _) in st["coils"].items():
        rig.bone(f"Coil.{label}", h, t, "Chest", roll=Y)
        rig.translate[f"Coil.{label}"] = f"_coil{label}"
    for g in (*st["capes"], st["front"]):
        rig.add_garment(g)


# ===== 动作 =====
REVIEW_POSE = ("Idle", 1)


def coils_pose(st, pose, out=0.0, rise=0.0, pitch=0.0):
    """线圈外展 out 弧度、前俯 pitch 弧度（负值前倾，用来抵消上身后仰）、沿轴升起 rise 米。"""
    for label, (_, _, axis) in st["coils"].items():
        sd = -1 if label == "L" else 1
        pose[f"Coil.{label}"] = R((X, pitch), (Y, sd * out))
        pose[f"_coil{label}"] = axis * rise * st["B"].s


def capes_wind(rig, st, pose, back, flare=None, side=None):
    for g in st["capes"]:
        rig.wind(pose, g, back, flare, side)


def idle_pose(rig, st, t):
    B = st["B"]
    p = idle(rig, B, t, breathe=0.020, sway=0.016, arms=0.05, spread=0.035, bend=0.10)
    for label in ("L", "R"):
        fingers(p, B, label, lambda i: 0.22 + 0.08 * math.sin(2 * t + i * 0.6))
    coils_pose(st, p)
    capes_wind(rig, st, p, lambda k, j: 0.05 + 0.03 * math.sin(t + k * 0.8 + j * 0.9),
               lambda k, j: 0.02, lambda k, j: 0.012 * math.sin(t + k * 0.9 + j * 0.6))
    rig.garment_pose(p, st["front"], lambda k, j: 0.03 + 0.02 * math.sin(t + j * 0.8))
    return p


def move_pose(rig, st, t):
    B = st["B"]
    p = gait(rig, B, t, stride=0.56, lift=0.20, stance=0.34, bob=0.04, lean=0.24, twist=0.12, arm=0.80, elbow=1.35,
             arm_in=0.30, knee_out=0.08, heel=0.06)
    for label in ("L", "R"):
        fingers(p, B, label, 0.25)
    coils_pose(st, p)
    capes_wind(rig, st, p, lambda k, j: 0.31 + 0.05 * math.sin(2 * t + k * 0.7 + j * 1.1),
               lambda k, j: 0.03, lambda k, j: 0.04 * math.sin(t + k * 0.6 + j * 0.8))
    panel_clear(rig, B, p, st["front"], 0.03 * math.sin(2 * t + 0.5), margin=0.06)
    return p


def cast_key(rig, st, stage):
    """雷隙：蓄势（右掌后引、身体右拧）→ 爆发前冲弓步右掌突刺 → 保持 → 收势。"""
    B = st["B"]
    s = B.s
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    if stage == 1:
        p["Pelvis"] = R((Z, -0.25), (X, -0.08))
        p["Spine"] = R((Z, -0.15))
        p["Chest"] = R((Z, -0.28), (X, 0.04))
        p["Head"] = R((Z, 0.30))
        plant_stance(rig, B, p, (-0.02, 0.18), (0.05, -0.16), 0.12, 0.15, -0.40, knee_out=0.2)
        arm_ik(rig, p, "R", (0.30 * s, -0.22 * s, B.z(1.18)), (1.0, -0.3, -0.6), hand_dir=(0.2, 0.3, -1.0))
        arm_ik(rig, p, "L", (-0.10 * s, 0.40 * s, B.z(1.42)), (-1.0, -0.3, -0.5), hand_dir=(0.2, 1.0, 0.1))
        fingers(p, B, "R", 1.1)
        fingers(p, B, "L", 0.3)
        coils_pose(st, p, 0.06, 0.02)
        capes_wind(rig, st, p, lambda k, j: 0.14, lambda k, j: 0.03)
    else:
        follow = stage == 3
        p["Pelvis"] = R((Z, 0.24), (X, -0.20))
        p["Spine"] = R((Z, 0.14), (X, -0.08))
        p["Chest"] = R((Z, 0.28 if not follow else 0.32), (X, -0.04))
        p["Neck"] = R((Z, -0.22), (X, 0.08))
        p["Head"] = R((Z, -0.30), (X, 0.10))
        plant_stance(rig, B, p, (-0.03, 0.50), (0.07, -0.42, 0.07), 0.20 if not follow else 0.18, 0.10, -0.45,
                     knee_out=0.15, pitch_r=0.55)
        arm_ik(rig, p, "R", (0.04 * s, 0.95 * s, B.z(1.46)), (1.0, 0.0, -1.0), hand_dir=(0.0, 1.0, 0.08))
        arm_ik(rig, p, "L", (-0.34 * s, -0.36 * s, B.z(1.12)), (-1.0, 0.2, -0.3), hand_dir=(-0.3, -0.6, -1.0))
        fingers(p, B, "R", lambda i: 0.3 if i == 0 else -0.05)
        fingers(p, B, "L", 0.7)
        coils_pose(st, p, 0.10, 0.04)
        capes_wind(rig, st, p, lambda k, j: 0.28 if not follow else 0.25, lambda k, j: 0.04,
                   lambda k, j: -0.06)
    panel_clear(rig, B, p, st["front"])
    return p


def channel_key(rig, st, stage):
    """狼雷：双臂 V 形高举引雷、仰首长啸、宽马步；线圈外展升起，披风被上升气流掀起。"""
    B = st["B"]
    s = B.s
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    p["Pelvis"] = R((X, 0.03))
    p["Spine"] = R((X, 0.07))
    p["Chest"] = R((X, 0.12))
    p["Neck"] = R((X, 0.08))
    p["Head"] = R((X, 0.16))
    plant_stance(rig, B, p, (-0.10, 0.02), (0.10, -0.02), 0.10, 0.30, -0.30, knee_out=0.3)
    for label, sd in (("L", -1), ("R", 1)):
        arm_ik(rig, p, label, (sd * 0.55 * s, 0.12 * s, B.z(2.25)), (sd * 0.3, -1.0, -0.3), hand_dir=(sd * 0.45, 0.1, 1.0))
        fingers(p, B, label, lambda i: 0.25 if i == 0 else 0.05, spread=1.0)
    # 线圈竖直升起、夹在头与双臂之间（上身后仰约 0.22 弧度，这里前俯抵消）
    coils_pose(st, p, -0.02, 0.10, pitch=-0.34)
    capes_wind(rig, st, p, lambda k, j: 0.30, lambda k, j: 0.18, lambda k, j: 0.0)
    rig.garment_pose(p, st["front"], lambda k, j: 0.14)
    return p


def animate(rig, st):
    rig.loop("Idle", 64, lambda t: idle_pose(rig, st, t))
    rig.loop("Move", 14, lambda t: move_pose(rig, st, t), step=1)
    k = [cast_key(rig, st, i) for i in range(4)]
    rig.keyed("Cast", [(1, k[0]), (8, k[1]), (14, k[2]), (20, k[3]), (32, k[0])])
    c = [channel_key(rig, st, i) for i in range(2)]
    rig.keyed("Channel", [(1, c[0]), (13, c[1]), (28, c[1]), (42, c[0])])
