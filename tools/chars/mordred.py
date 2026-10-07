"""莫德雷德 · 熔炉骑士（Mordred, The Furnace Knight）。

设定：焦黑锻铁重甲 + 青铜 / 赤铜滚边 + 熔橙光缝。胸口是哥特尖拱炉门（左右两扇格栅门，门后是炽热煤床），
背负锅炉与双烟囱（余烬口沿，技能时喷出火舌），牛角巨盔带横向光缝与呼吸格栅，五层巨型肩甲带散热肋，
钟形巨护手；背后竖挂巨型斩刃（刚性挂 Chest，刀柄从两座烟囱之间伸出），前垂焦灼破边罩袍。
动作：Idle（重装待机）/ Move（重步行进）/ Cast「断层」（双拳举过头顶砸地）/
Channel「烈日处决」（双臂高举、炉门洞开、烟囱喷火、马步）。
"""

import math

from mathutils import Matrix, Vector

from kit.core import (TAU, clamp, crack_maps, ellipsoid, filigree_maps, finish, gem, interp, invdist, join, lathe,
                      lerp, orient, plate, projector, radial, rigid, ring_points, smoothstep, spike, surface,
                      transform, trim, tube, bands)
from kit.humanoid import (SIDES, Body, add_skeleton, cuisse, greave, hand, limb_frame, limb_plate, poleyn,
                          rerebrace, sabaton, shell, vambrace)
from kit.motion import Legs, fingers, gait, idle
from kit.rig import R, X, Y, Z

from chars._forge_helpers import (RaggedPanel, arm_ik, axis_frame, blade_maps, coal_maps, ensure_uv, gorget_lite,
                                  hammered_maps, mail_maps, panel_clear, pauldron_lames, plant_stance,
                                  scorch_cloth_maps, suit_arm_uv, suit_leg_uv, suit_torso_uv, tri_report, utube,
                                  uv_scale)

TITLE = "Mordred"
ACCENT = (1.0, 0.67, 0.39)
CLIPS = ("Idle", "Move", "Cast", "Channel")
GAME_TRIS = 62000
MOLTEN = (1.0, 0.42, 0.12)       # 熔缝 / 裂纹发光色（比主题色更深，AgX 下高亮处自然偏黄白）
IRON = (0.052, 0.046, 0.043)
BRONZE = (0.50, 0.30, 0.14)


def materials(ctx):
    M = ctx.M
    ctx.mat("iron", "scorched cast iron", IRON, metal=0.9, rough=0.34, coat=0.05, coat_rough=0.35)
    # 贴图按 sRGB 解读：底色给 sRGB 编码值（约为 IRON 的显示值），锤坑法线加深到近看能看出锻打起伏
    ctx.texture("iron", hammered_maps((0.125, 0.112, 0.104), size=1024, seed=5, cells=14, dent=10.0,
                                      ridge_rgb=(0.20, 0.09, 0.04), pits=0.0016), normal_strength=1.0)
    ctx.mat("hot", "cracked furnace iron", (0.045, 0.034, 0.030), metal=0.75, rough=0.5)
    ctx.texture("hot", crack_maps(MOLTEN, base_rgb=(0.050, 0.038, 0.033), size=1024, seed=12, cells=6, width=0.04),
                emit_strength=2.7, normal_strength=0.9)
    ctx.mat("bronze", "forged bronze", BRONZE, metal=1.0, rough=0.32)
    ctx.texture("bronze", filigree_maps(BRONZE, (0.22, 0.12, 0.055), size=1024, seed=6, density=20, width=1),
                normal_strength=0.3)
    ctx.mat("copper", "red copper rivets", (0.70, 0.33, 0.20), metal=1.0, rough=0.28)
    ctx.mat("mail", "blackened chainmail", (0.060, 0.056, 0.054), metal=0.9, rough=0.40)
    ctx.texture("mail", mail_maps((0.060, 0.056, 0.054), size=1024, rings=40), normal_strength=1.0)
    ctx.mat("tabard", "scorched tabard", (0.085, 0.032, 0.020), rough=0.85, sheen=0.15, sheen_tint=(1.0, 0.6, 0.4),
            spec=0.3)
    ctx.texture("tabard", scorch_cloth_maps(MOLTEN, w=512, h=1024, seed=8), emit_strength=2.4, normal_strength=0.5)
    ctx.mat("lining", "ember-red lining", (0.12, 0.030, 0.015), rough=0.55, sheen=0.3, sheen_tint=(1, 0.5, 0.3))
    ctx.mat("core", "furnace core coals", (1.0, 0.5, 0.2), emit=MOLTEN, strength=9.0)
    ctx.texture("core", coal_maps(MOLTEN, size=512, cells=6, seed=3), emit_strength=9.0, normal_strength=0.4)
    ctx.mat("glow", "molten glow", (1.0, 0.62, 0.32), emit=(1.0, 0.55, 0.22), strength=8.0)
    ctx.mat("flame", "chimney flame glow", (1.0, 0.5, 0.18), emit=(1.0, 0.40, 0.10), strength=6.5)
    ctx.mat("inlay", "molten seam inlay", (0.6, 0.30, 0.10), emit=MOLTEN, strength=4.2)
    ctx.mat("hem", "ember hem light", (0.5, 0.25, 0.10), emit=MOLTEN, strength=4.5)
    ctx.mat("blade", "relic cleaver steel", (0.13, 0.125, 0.12), metal=1.0, rough=0.30)
    ctx.texture("blade", blade_maps(MOLTEN, w=1024, h=256, band=(0.15, 0.33), span=(0.06, 0.58)),
                emit_strength=3.0, normal_strength=0.4)
    ctx.mat("edge", "honed edge steel", (0.62, 0.60, 0.58), metal=1.0, rough=0.14)
    return M


# ===== 胸甲与炉门 =====
G, TH, DEPTH = 0.024, 0.010, 0.034           # 胸甲外扩、板厚、炉膛凹陷深度（米）
FURN = (1.37, 1.485, 1.600, 0.090)            # 炉门尖拱：拱底 / 拱脚 / 拱顶高度（身高系数）与半宽（米）


def bulge(B, a, z):
    """桶形胸：胸口中央向前鼓出。"""
    return 0.020 * B.s * math.exp(-((z - B.z(1.50)) / (0.11 * B.s)) ** 2) * max(0.0, math.cos(a)) ** 2


def arch_params(B):
    zb, zs, za, w = B.z(FURN[0]), B.z(FURN[1]), B.z(FURN[2]), FURN[3] * B.s
    h = za - zs
    e = (h * h - w * w) / (2 * w)
    return zb, zs, za, w, e, w + e


def arch_hw(B, z):
    """尖拱在高度 z 处的半宽：拱脚以下为常宽，以上为两段圆弧交于拱顶。"""
    zb, zs, za, w, e, r = arch_params(B)
    if z <= zs:
        return w
    return max(0.0, math.sqrt(max(0.0, r * r - (z - zs) ** 2)) - e)


def arch_top(B, x):
    zb, zs, za, w, e, r = arch_params(B)
    return zs + math.sqrt(max(0.0, r * r - (abs(x) + e) ** 2))


def arch_in(B, x, z):
    """点 (x, z) 到尖拱边界的近似内距（正值在拱内）。"""
    zb, zs, za, w, e, r = arch_params(B)
    if z >= za:
        return -(z - za) - abs(x)
    return min(arch_hw(B, max(z, zb)) - abs(x), z - zb)


def arch_half(B, o=0.0, n=22):
    """尖拱左半轮廓（左下拱底 → 左拱脚 → 拱顶），o>0 向外扩。返回 [(x, z), ...]。"""
    zb, zs, za, w, e, r = arch_params(B)
    zb, za, w = zb - o, za + o * 1.5, w + o
    h = za - zs
    e = (h * h - w * w) / (2 * w)
    r = w + e
    pts = [(-w, lerp(zb, zs, i / 5)) for i in range(5)]
    f0, f1 = math.pi, math.atan2(h, -e)
    for i in range(n + 1):
        f = lerp(f0, f1, i / n)
        pts.append((e + r * math.cos(f), zs + r * math.sin(f)))
    return pts


def arch_loop(B, o=0.0):
    """完整闭合尖拱轮廓（含底边）。"""
    left = arch_half(B, o)
    right = [(-x, z) for x, z in reversed(left)][1:]
    zb, w = left[0][1], -left[0][0]
    bottom = [(lerp(w, -w, i / 6), zb) for i in range(1, 6)]
    return left + right + bottom


def rivet(ctx, name, p, r, mat, spec):
    """低面数铆钉。"""
    return ctx.part(ellipsoid(name, p, (r,) * 3, [mat], 8, 5), spec)


def chest_x(B, a, z):
    return (B.torso_r(z)[0] + G) * math.sin(a)


def fp(B, x, z, g):
    """胸甲正面坐标 (x, z) → 胸甲外表面上方 g 米处的点（与胸甲曲面、桶形鼓出一致）。"""
    a = math.asin(clamp(x / (B.torso_r(z)[0] + G), -0.999, 0.999))
    return B.torso_point(a, z, G + bulge(B, a, z) + g)


def chest_shape(B):
    def shape(a, z):
        d = 0.0
        if math.cos(a) > 0.3:
            d = DEPTH * smoothstep(-0.002 * B.s, 0.012 * B.s, arch_in(B, chest_x(B, a, z), z))
        return bulge(B, a, z) - d
    return shape


def build_cuirass(ctx, B, M):
    s = B.s
    spec = bands([(B.z(1.355), "Chest"), (B.z(1.27), "Spine")])
    zt = lambda a: B.z(1.668) - 0.02 * s * max(0.0, math.cos(a)) ** 8
    zb = lambda a: B.z(1.300) - 0.04 * s * max(0.0, math.cos(a)) ** 6
    shell(ctx, B, f"{ctx.title} cuirass front", zt, zb, G, M["iron"], spec, a0=-1.10, a1=1.10, thick=TH, nu=76,
          nv=42, sub=0, trims=(M["bronze"], 0.0042 * s), shape=chest_shape(B))
    pt = shell(ctx, B, f"{ctx.title} cuirass back", zt, zb, G, M["iron"], spec, a0=1.10, a1=TAU - 1.10, thick=TH,
               nu=46, nv=22, sub=0)
    for v in (0.0, 1.0):
        pts = [radial(pt(i / 47, v), 0.011 * s) for i in range(48)]
        ctx.part(trim(f"{ctx.title} cuirass back trim {v}", pts, 0.0042 * s, M["bronze"]), spec)
    # 侧缝铆钉
    for a in (-1.10, 1.10):
        for z in [B.z(1.34 + i * 0.056) for i in range(6)]:
            rivet(ctx, f"{ctx.title} side rivet", B.torso_point(a, z, G + TH + 0.009 * s), 0.0070 * s, M["copper"], spec)
    # 背甲熔缝（锅炉两侧，斩刃遮不住的位置）
    paths = [[(0.165, 1.625), (0.190, 1.570), (0.190, 1.450), (0.215, 1.405)], [(0.150, 1.385), (0.185, 1.340)]]
    for sd in (-1, 1):
        for k, path in enumerate(paths):
            pts = []
            for (x0, z0), (x1, z1) in zip(path, path[1:]):
                for i in range(6):
                    t = i / 6
                    pts.append(B.on_torso(sd * lerp(x0, x1, t) * s, B.z(lerp(z0, z1, t)), G + TH + 0.0014 * s, back=True))
            end = B.on_torso(sd * path[-1][0] * s, B.z(path[-1][1]), G + TH + 0.0014 * s, back=True)
            ctx.part(trim(f"{ctx.title} back seam {sd}{k}", pts + [end], 0.0022 * s, M["inlay"]), spec)
            ctx.part(ellipsoid(f"{ctx.title} back via {sd}{k}", end, (0.0046 * s,) * 3, [M["glow"]], 8, 5), spec)


def build_furnace(ctx, B, M):
    """胸口尖拱炉门：固定青铜门框 + 外圈铸铁门楣与铆钉 + 左右两扇格栅门（挂 Door.L/R，终结技时洞开）+ 煤床。"""
    s = B.s
    zb, zs, za, w, e, r = arch_params(B)
    chest = rigid("Chest")
    # 煤床：铺满拱内（边缘埋进炉膛内壁）
    def core_pt(u, v):
        z = lerp(za + 0.004 * s, zb - 0.004 * s, v)
        hw = arch_hw(B, min(z, za)) + 0.006 * s
        return fp(B, (2 * u - 1) * hw, z, TH - DEPTH + 0.003 * s)
    core = surface(f"{ctx.title} furnace core", core_pt, 18, 20, [M["core"]])
    orient(core, lambda c: Vector((0, 0, c.z)))
    ctx.part(core, chest)
    # 固定门框（青铜）+ 门楣（铸铁）+ 铆钉 + 拱心石
    loop = arch_loop(B, 0.010 * s)
    ctx.part(trim(f"{ctx.title} furnace frame", [fp(B, x, z, TH + 0.004 * s) for x, z in loop], 0.0105 * s,
                  M["bronze"], closed=True), chest)
    outer = arch_loop(B, 0.030 * s)
    ctx.part(trim(f"{ctx.title} furnace lintel", [fp(B, x, z, TH + 0.002 * s) for x, z in outer], 0.0080 * s,
                  M["iron"], closed=True), chest)
    for i, (x, z) in enumerate(outer):
        if i % 4 == 1:
            rivet(ctx, f"{ctx.title} lintel rivet", fp(B, x, z, TH + 0.009 * s), 0.0062 * s, M["copper"], chest)
    # 拱两侧的哥特小尖塔
    for sd in (-1, 1):
        x = sd * (w + 0.040 * s)
        ctx.part(spike(f"{ctx.title} furnace pinnacle", fp(B, x, zb + 0.10 * s, TH), fp(B, x, zs + 0.13 * s, TH + 0.012 * s),
                       0.012 * s, [M["bronze"]], sides=4), chest)
        ctx.part(gem(f"{ctx.title} pinnacle gem", fp(B, x, zb + 0.085 * s, TH + 0.008 * s), 0.0065 * s, M["glow"],
                     (1, 0.6, 1)), chest)
    key = fp(B, 0, za + 0.034 * s, TH + 0.006 * s)
    ctx.part(ellipsoid(f"{ctx.title} keystone", key, (0.020 * s, 0.011 * s, 0.024 * s), [M["bronze"]], 16, 10), chest)
    ctx.part(gem(f"{ctx.title} keystone gem", key + Vector((0, 0.010 * s, 0)), 0.0085 * s, M["glow"],
                 (0.8, 0.5, 1.3)), chest)
    # 两扇格栅门
    doors = {}
    for sd, label in SIDES:
        spec = rigid(f"Door.{label}")
        g = TH + 0.004 * s
        half = [(-sd * x, z) for x, z in arch_half(B, 0.0)]
        ctx.part(trim(f"{ctx.title} door frame {label}", [fp(B, x, z, g) for x, z in half], 0.0085 * s,
                      M["bronze"]), spec)
        ctx.part(trim(f"{ctx.title} door stile {label}", [fp(B, sd * 0.004 * s, lerp(zb, za - 0.004 * s, i / 10), g)
                                                           for i in range(11)], 0.0088 * s, M["bronze"]), spec)
        ctx.part(trim(f"{ctx.title} door sill {label}", [fp(B, sd * lerp(0.004, 0.090, i / 8) * s, zb, g)
                                                          for i in range(9)], 0.0085 * s, M["bronze"]), spec)
        for x in (0.024, 0.047, 0.069):
            top = arch_top(B, x * s) - 0.006 * s
            pts = [fp(B, sd * x * s, lerp(zb + 0.006 * s, top, i / 9), g - 0.001 * s) for i in range(10)]
            ctx.part(tube(f"{ctx.title} door bar {label}", pts, [0.0064 * s] * 10, [M["iron"]], n=8, per=1), spec)
        for zr in (1.425, 1.535):
            z = B.z(zr)
            hw = arch_hw(B, z) - 0.004 * s
            if hw <= 0.01 * s:
                continue
            pts = [fp(B, sd * lerp(0.004 * s, hw, i / 7), z, g - 0.003 * s) for i in range(8)]
            ctx.part(tube(f"{ctx.title} door rail {label}", pts, [0.0052 * s] * 8, [M["iron"]], n=8, per=1), spec)
        # 门环：每扇门中央一枚发光铆
        ctx.part(gem(f"{ctx.title} door stud {label}", fp(B, sd * 0.047 * s, B.z(1.48), g + 0.007 * s), 0.0070 * s,
                     M["glow"], (1, 0.6, 1)), spec)
        hinge = fp(B, sd * w, zb, g)
        doors[label] = (hinge.copy(), Vector((hinge.x, hinge.y, zs)))
        for zh in (1.395, 1.450):
            ctx.part(ellipsoid(f"{ctx.title} hinge {label}", fp(B, sd * (w + 0.006 * s), B.z(zh), g + 0.002 * s),
                               (0.0075 * s, 0.0075 * s, 0.016 * s), [M["copper"]], 10, 8), chest)
    # 胸甲上的熔缝：从炉门向两侧放射
    paths = [[(0.112, 1.575), (0.150, 1.605), (0.200, 1.610)],
             [(0.118, 1.500), (0.160, 1.488), (0.205, 1.488)],
             [(0.110, 1.410), (0.150, 1.385), (0.195, 1.385)],
             [(0.050, 1.345), (0.070, 1.320)]]
    for sd, label in SIDES:
        for k, path in enumerate(paths):
            pts = []
            for (x0, z0), (x1, z1) in zip(path, path[1:]):
                for i in range(6):
                    t = i / 6
                    pts.append(fp(B, sd * lerp(x0, x1, t) * s, B.z(lerp(z0, z1, t)), TH + 0.0014 * s))
            end = fp(B, sd * path[-1][0] * s, B.z(path[-1][1]), TH + 0.0014 * s)
            pts.append(end)
            ctx.part(trim(f"{ctx.title} heat seam {label}{k}", pts, 0.0022 * s, M["inlay"]), chest)
            ctx.part(ellipsoid(f"{ctx.title} seam via {label}{k}", end, (0.0046 * s,) * 3, [M["glow"]], 10, 6), chest)
    return doors


# ===== 腰部 =====
def build_waist(ctx, B, M):
    s = B.s
    shell(ctx, B, f"{ctx.title} belt", B.z(1.292), B.z(1.244), 0.040 * s, M["bronze"], invdist(["Pelvis", "Spine"]),
          nu=64, nv=4, thick=0.007 * s, sub=0)
    c = B.on_torso(0, B.z(1.268), 0.050 * s)
    buckle = [(-0.046, -0.030), (0.046, -0.030), (0.060, 0.0), (0.046, 0.030), (-0.046, 0.030), (-0.060, 0.0)]
    ctx.part(plate(f"{ctx.title} buckle", [(x * s, y * s) for x, y in buckle], 0.012 * s, [M["bronze"]], origin=c,
                   xaxis=(1, 0, 0), yaxis=(0, 0, 1), bev=0.002 * s), rigid("Pelvis"))
    ctx.part(trim(f"{ctx.title} buckle ring", ring_points(c + Vector((0, 0.007 * s, 0)), (0, 1, 0), 0.020 * s, 20),
                  0.0032 * s, M["copper"], closed=True), rigid("Pelvis"))
    ctx.part(gem(f"{ctx.title} buckle gem", c + Vector((0, 0.009 * s, 0)), 0.012 * s, M["glow"], (1.0, 0.5, 1.0)),
             rigid("Pelvis"))
    for k, (zt, zb, g) in enumerate(((1.255, 1.165, 0.046), (1.185, 1.095, 0.054), (1.115, 1.030, 0.062))):
        a0, a1 = 0.74, TAU - 0.74
        shell(ctx, B, f"{ctx.title} fauld {k}", B.z(zt), lambda a, zb=zb: B.z(zb) - 0.03 * s * max(0.0, math.cos(a)) ** 4,
              g * s, M["iron"], rigid("Pelvis"), a0=a0, a1=a1, nu=50, nv=6, thick=0.007 * s, sub=0,
              trims=(M["bronze"], 0.0032 * s))
        for i in range(9):
            a = lerp(a0 + 0.12, a1 - 0.12, i / 8)
            z = B.z(zb + 0.014) - 0.03 * s * max(0.0, math.cos(a)) ** 4
            rivet(ctx, f"{ctx.title} fauld rivet", B.torso_point(a, z, (g + 0.010) * s), 0.0055 * s, M["copper"],
                  rigid("Pelvis"))


# ===== 肩与臂 =====
def build_arms(ctx, B, M):
    s = B.s
    for side, label in SIDES:
        lames = [(0.00, 0.80, 1.000, M["hot"], 0.82), (0.52, 1.10, 0.965, M["iron"], 0.68),
                 (0.84, 1.38, 0.930, M["iron"], 0.54), (1.14, 1.66, 0.895, M["iron"], 0.42),
                 (1.42, 1.92, 0.860, M["iron"], 0.32)]
        lp, sh = pauldron_lames(ctx, B, side, label, lames, radius=0.215, spread=1.42, rise=1.14, tilt=0.20,
                                ridge=0.035, thick=0.010, trim_mat=M["bronze"], trim_r=0.0042, nu=38, nv=10)
        top = rigid(("Chest", 0.82), (f"UpperArm.{label}", 0.18))
        # 首片散热肋 + 铆钉
        for t in (0.30, 0.52, 0.74):
            pts = [lp(0, u, t) for u in [lerp(-0.78, 0.78, i / 22) for i in range(23)]]
            pts = [p + (p - sh).normalized() * 0.013 * s for p in pts]
            ctx.part(trim(f"{ctx.title} pauldron rib {label}", pts, 0.0062 * s, M["bronze"]), top)
        for u in [lerp(-0.72, 0.72, i / 6) for i in range(7)]:
            p = lp(0, u, 0.93)
            rivet(ctx, f"{ctx.title} pauldron rivet {label}", p + (p - sh).normalized() * 0.013 * s, 0.0068 * s,
                  M["copper"], top)
        a = B.arms[label]
        rerebrace(ctx, B, side, label, M["iron"], M["bronze"], r=(0.064, 0.054), nu=28, nv=10, sub=0)
        ctx.part(ellipsoid(f"{ctx.title} couter {label}", a["elbow"] + Vector((side * 0.020 * s, -0.036 * s, 0)),
                           (0.044 * s, 0.040 * s, 0.048 * s), [M["iron"]], 16, 10),
                 rigid((f"UpperArm.{label}", 0.5), (f"Forearm.{label}", 0.5)))
        vambrace(ctx, B, side, label, M["iron"], M["bronze"], inlay=M["inlay"], r=(0.050, 0.056),
                 spur=(M["bronze"], 0.075), sub=0)
        # 钟形巨护手：裂纹熔铁，腕口大幅外翻
        e, w = a["elbow"], a["wrist"]
        fdir = (w - e).normalized()
        c0, c1 = e.lerp(w, 0.48), w + fdir * 0.030 * s
        limb_plate(ctx, f"{ctx.title} gauntlet cuff {label}", c0, c1, 0.074 * s, 0.082 * s, M["hot"],
                   rigid(f"Forearm.{label}"), Vector((side, -0.35, 0.25)), closed=True, flare1=0.030 * s,
                   thick=0.007 * s, trim_mat=M["bronze"], trim_r=0.0036 * s, nu=28, nv=10, sub=0)
        axis, o, wv = limb_frame(c0, c1, Vector((side, -0.35, 0.25)))
        mid = c0.lerp(c1, 0.35)
        for i in range(6):
            th = i / 6 * TAU
            rivet(ctx, f"{ctx.title} cuff stud {label}", mid + (o * math.cos(th) + wv * math.sin(th)) * 0.086 * s,
                  0.0062 * s, M["copper"], rigid(f"Forearm.{label}"))
        # 拳背大甲片：弧形锻铁板 + 青铜脊线 / 指根滚边 + 赤铜铆钉，让巨护手的拳头足够厚重
        H = B.hands[label]
        wr, f, n, sv = H["wrist"], H["f"], H["n"], H["s"]
        k = 1.5 * s

        def hp(u, v, wr=wr, f=f, n=n, sv=sv):
            uu = lerp(-1.0, 1.0, u)
            w = lerp(0.031, 0.037, v) * k
            out = (0.0205 + 0.0080 * (1 - uu * uu) - 0.004 * v * v) * k
            return wr + f * lerp(0.002, 0.082, v) * k + sv * uu * w - n * out
        hand_spec = rigid(f"Hand.{label}")
        hplate = surface(f"{ctx.title} hand plate {label}", hp, 12, 8, [M["iron"]])
        orient(hplate, lambda c, wr=wr, f=f: wr + f * 0.04 * k)
        ctx.part(finish(hplate, 0.005 * s, -1, 0), hand_spec)
        ridge = [hp(0.5, v) - n * 0.004 * s for v in [lerp(0.08, 0.92, i / 8) for i in range(9)]]
        ctx.part(trim(f"{ctx.title} hand ridge {label}", ridge, 0.0040 * s, M["bronze"]), hand_spec)
        ctx.part(trim(f"{ctx.title} hand rim {label}", [hp(u, 1.0) - n * 0.002 * s for u in [i / 10 for i in range(11)]],
                      0.0036 * s, M["bronze"]), hand_spec)
        for u, v in ((0.16, 0.25), (0.84, 0.25), (0.16, 0.80), (0.84, 0.80)):
            rivet(ctx, f"{ctx.title} hand rivet {label}", hp(u, v) - n * 0.004 * s, 0.0050 * s, M["copper"], hand_spec)


# ===== 腿 =====
def build_legs(ctx, B, M):
    s = B.s
    for side, label in SIDES:
        L = B.legs[label]
        cuisse(ctx, B, side, label, M["iron"], M["bronze"], r=(0.104, 0.088), nu=28, nv=12, sub=0)
        poleyn(ctx, B, side, label, M["iron"], M["bronze"], M["glow"], size=0.080, wing=0.06)
        greave(ctx, B, side, label, M["iron"], M["bronze"], r=(0.078, 0.060), nv=14, sub=0)
        sabaton(ctx, B, side, label, M["iron"], M["bronze"], width=0.064, height=0.07, toe_mat=M["bronze"])
        knee, ankle = L["knee"], L["ankle"]
        # 腿甲正面熔缝
        axis, o, wv = limb_frame(L["hip"], knee, Vector((side * 0.55, 1, 0)))
        pts = []
        for i in range(14):
            v = lerp(0.12, 0.85, i / 13)
            rr = (lerp(0.104, 0.088, v) * B.limb + 0.006 * math.sin(v * math.pi) + 0.006 + 0.0075) * s
            pts.append(L["hip"].lerp(knee, lerp(0.10, 0.88, v)) + o * rr)
        ctx.part(trim(f"{ctx.title} cuisse seam {label}", pts, 0.0024 * s, M["inlay"]), rigid(f"Thigh.{label}"))
        # 重靴踝箍
        limb_plate(ctx, f"{ctx.title} ankle cuff {label}", knee.lerp(ankle, 0.80), ankle - Vector((0, 0, 0.012 * s)),
                   0.086 * s, 0.090 * s, M["iron"], rigid(f"Shin.{label}"), Vector((0, 1, 0)), closed=True,
                   flare1=0.012 * s, thick=0.006 * s, trim_mat=M["bronze"], trim_r=0.0032 * s, nu=26, nv=6, sub=0)
        # 胫甲正面熔缝
        axis, o, wv = limb_frame(knee, ankle, Vector((0, 1, 0)))
        pts = []
        for i in range(14):
            t = lerp(0.22, 0.76, i / 13)
            v = (t - 0.10) / 0.83
            rr = (lerp(0.078, 0.060, v) * B.limb + 0.010 * math.sin(v * math.pi) + 0.006 + 0.0075) * s
            pts.append(knee.lerp(ankle, t) + o * rr)
        ctx.part(trim(f"{ctx.title} greave seam {label}", pts, 0.0024 * s, M["inlay"]), rigid(f"Shin.{label}"))
        # 大腿外侧三层挂甲
        for k in range(3):
            limb_plate(ctx, f"{ctx.title} tasset {label}{k}", L["hip"] + Vector((0, 0, (0.13 - k * 0.06) * s)),
                       L["hip"].lerp(L["knee"], 0.34 - k * 0.08), (0.138 + k * 0.010) * s, (0.130 + k * 0.010) * s,
                       M["iron"], rigid(f"Thigh.{label}"), Vector((side, 0.30, 0)), arc=1.05, thick=0.007 * s,
                       trim_mat=M["bronze"], trim_r=0.0030 * s, rims=(1,), nu=22, nv=8, sub=0)


# ===== 牛角巨盔 =====
def build_helm(ctx, B, M):
    s = B.s
    hc = Vector((0, 0.018 * s, B.z(1.885)))
    rx, ry = 0.132 * s, 0.142 * s
    prof = [(0.0, (0.00, 0.150)), (0.07, (0.46, 0.148)), (0.16, (0.78, 0.140)), (0.28, (0.94, 0.118)),
            (0.42, (1.00, 0.074)), (0.60, (1.00, 0.000)), (0.80, (0.97, -0.075)), (1.0, (1.05, -0.138))]
    eye_z, slit_w = hc.z + 0.016 * s, 0.080 * s

    def hp(u, v):
        a = u * TAU
        r, dz = interp(prof, v)
        ca, sa = math.cos(a), math.sin(a)
        k = (abs(ca) ** 3 + abs(sa) ** 3) ** (-1 / 3)          # 超椭圆截面：桶盔更方
        front = max(0.0, ca)
        x = rx * r * sa * k
        y = ry * r * ca * k
        z = hc.z + dz * s
        prow = 0.020 * s * math.exp(-(x / (0.020 * s)) ** 2) * front ** 2 * smoothstep(0.30, 0.95, v)
        groove = 0.0
        if front > 0.3:
            groove -= 0.013 * s * math.exp(-((z - eye_z) / (0.0085 * s)) ** 2) * (1 - smoothstep(slit_w * 0.9, slit_w * 1.1, abs(x)))
            groove += 0.008 * s * math.exp(-((z - eye_z - 0.022 * s) / (0.008 * s)) ** 2) * front ** 1.5
        flare = 0.012 * s * smoothstep(0.84, 1.0, v)
        d = Vector((x, y, 0)).normalized() if r > 1e-4 else Vector((0, 0, 0))
        return Vector((x, y + hc.y + prow + groove * front, z)) + d * flare
    helm = surface(f"{ctx.title} helm", hp, 84, 46, [M["iron"]])
    orient(helm, lambda c: hc)
    helm = finish(helm, 0.005 * s, -1, 0)
    head = rigid("Head")
    ctx.part(helm, head)
    proj = projector(helm, (0, -1, 0))
    slit = [proj(Vector((x, 1, eye_z - 0.005 * s * (x / slit_w) ** 2)), 0.0010 * s)
            for x in [lerp(-slit_w, slit_w, i / 20) for i in range(21)]]
    ctx.part(tube(f"{ctx.title} visor slit", slit, [0.0036 * s] * 21, [M["glow"]], n=8, fx=0.6, up=(0, 0, 1)), head)
    # 呼吸格栅：六道竖向光槽 + 青铜框
    for x in (-0.050, -0.030, -0.010, 0.010, 0.030, 0.050):
        pts = [proj(Vector((x * s, 1, eye_z - lerp(0.032, 0.078, i / 7) * s)), 0.0008 * s) for i in range(8)]
        ctx.part(tube(f"{ctx.title} breath slot", pts, [0.0026 * s] * 8, [M["glow"]], n=6, fx=0.55), head)
    box = [(-0.064, 0.025), (0.064, 0.025), (0.064, 0.085), (-0.064, 0.085)]
    frame = []
    for (x0, d0), (x1, d1) in zip(box, box[1:] + box[:1]):
        for i in range(8):
            t = i / 8
            frame.append(proj(Vector((lerp(x0, x1, t) * s, 1, eye_z - lerp(d0, d1, t) * s)), 0.0022 * s))
    ctx.part(trim(f"{ctx.title} grille frame", frame, 0.0030 * s, M["bronze"], closed=True), head)
    # 眉带、铆钉、下缘
    band = [radial(hp(i / 96, 0.43), 0.004 * s, hc.y) for i in range(96)]
    ctx.part(trim(f"{ctx.title} brow band", band, 0.0050 * s, M["bronze"], closed=True), head)
    for i in range(20):
        rivet(ctx, f"{ctx.title} helm rivet", radial(hp(i / 20 + 0.025, 0.43), 0.010 * s, hc.y), 0.0050 * s,
              M["copper"], head)
    rim = [radial(hp(i / 96, 1.0), 0.004 * s, hc.y) for i in range(96)]
    ctx.part(trim(f"{ctx.title} helm rim", rim, 0.0048 * s, M["bronze"], closed=True), head)
    # 顶脊
    path = [hp(0.0, v) for v in [0.43 - i / 24 * 0.43 for i in range(25)]]
    path += [hp(0.5, v) for v in [i / 24 * 0.62 for i in range(25)]][1:]

    def crest_at(t):
        f = t * (len(path) - 1)
        i = min(len(path) - 2, int(f))
        return path[i].lerp(path[i + 1], f - i)

    def crest_pt(u, v):
        p = crest_at(u)
        n = (p - hc).normalized()
        return p + n * (0.024 * s * math.sin(math.pi * u) ** 0.6 * v - 0.004 * s)
    ctx.part(finish(surface(f"{ctx.title} crest", crest_pt, 48, 5, [M["iron"]]), 0.007 * s, 0, 0), head)
    ctx.part(trim(f"{ctx.title} crest edge", [crest_pt(i / 48, 1.0) for i in range(49)], 0.0032 * s, M["bronze"]),
             head)
    # 牛角：裂纹熔铁，向外、向前上方弯起；根部青铜箍
    horn = [(0.104, 0.023, 1.972), (0.158, 0.030, 1.990), (0.232, 0.053, 2.018), (0.300, 0.090, 2.072),
            (0.334, 0.133, 2.146), (0.330, 0.168, 2.226), (0.308, 0.190, 2.292)]
    radii = [0.042, 0.040, 0.033, 0.026, 0.018, 0.010, 0.0]
    for sd, label in SIDES:
        pts = [Vector((sd * x * s, y * s, B.z(z))) for x, y, z in horn]
        ctx.part(utube(f"{ctx.title} horn {label}", pts, [r * s for r in radii], [M["hot"]], n=16, per=6, uv=(2, 3)),
                 head)
        for k, (i, rr, tr, mat) in enumerate(((1, 0.041, 0.0062, M["bronze"]), (2, 0.034, 0.0040, M["copper"]))):
            tang = (pts[i + 1] - pts[i - 1]).normalized()
            ctx.part(trim(f"{ctx.title} horn ring {label}{k}", ring_points(pts[i], tang, rr * s, 20), tr * s, mat,
                          closed=True), head)
        # 颊侧圆形炉口
        pr = projector(helm, (-sd, 0, 0))
        vc = pr(Vector((sd * 0.5, hc.y + 0.030 * s, eye_z - 0.040 * s)), 0.002 * s)
        ctx.part(trim(f"{ctx.title} cheek vent {label}", ring_points(vc, (sd, 0.25, 0), 0.016 * s, 18), 0.0034 * s,
                      M["bronze"], closed=True), head)
        ctx.part(ellipsoid(f"{ctx.title} cheek glow {label}", vc, (0.004 * s, 0.012 * s, 0.012 * s), [M["glow"]], 12, 8),
                 head)
    return hc


# ===== 背部：锅炉 + 双烟囱 =====
BOILER_C = (0.0, -0.235, 1.50)


def chimney_frame(B, sd):
    base = Vector((sd * 0.14, -0.245, 1.515)) * B.s
    axis = Vector((sd * 0.15, -0.10, 1.0)).normalized()
    return base, axis, axis_frame(base, axis)


def build_back(ctx, B, M):
    s = B.s
    chest = rigid("Chest")
    c = Vector(BOILER_C) * s
    prof = [(0.0, 0.215), (0.040, 0.212), (0.062, 0.200), (0.074, 0.182), (0.078, 0.160), (0.078, -0.160),
            (0.074, -0.182), (0.062, -0.200), (0.040, -0.212), (0.0, -0.215)]
    boiler = lathe(f"{ctx.title} boiler", [(r * s, z * s) for r, z in prof], [M["iron"]], segments=32, sy=0.96)
    transform(boiler, Matrix.Translation(c) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
    ctx.part(boiler, chest)
    for x in (-0.185, -0.100, 0.100, 0.185):
        ctx.part(trim(f"{ctx.title} boiler band", ring_points(c + Vector((x * s, 0, 0)), (1, 0, 0), 0.081 * s, 28),
                      0.0068 * s, M["copper"], closed=True), chest)
    for sd in (-1, 1):
        cap = c + Vector((sd * 0.214 * s, 0, 0))
        ctx.part(trim(f"{ctx.title} gauge bezel", ring_points(cap, (1, 0, 0), 0.030 * s, 20), 0.0050 * s,
                      M["bronze"], closed=True), chest)
        ctx.part(gem(f"{ctx.title} gauge glass", cap, 0.024 * s, M["glow"], (0.35, 1.0, 1.0)), chest)
    flames = {}
    for sd, label in SIDES:
        base, axis, F = chimney_frame(B, sd)
        cp = [(0.062, 0.668), (0.076, 0.662), (0.080, 0.640), (0.077, 0.616), (0.064, 0.600), (0.055, 0.585),
              (0.052, 0.540), (0.051, 0.300), (0.054, 0.090), (0.064, 0.072), (0.084, 0.055), (0.086, 0.0)]
        stack = lathe(f"{ctx.title} chimney {label}", [(r * s, z * s) for r, z in cp], [M["iron"]], segments=28)
        uv_scale(stack, 1.0, 2.0)                  # 烟囱高约为周长两倍，纵向 UV 加倍免得锤痕被拉长
        stack = finish(stack, 0.006 * s, -1, 0)
        transform(stack, F)
        ctx.part(stack, chest)
        for h in (0.14, 0.30, 0.46):
            ring = [F @ Vector((math.cos(t) * 0.0565 * s, math.sin(t) * 0.0565 * s, h * s))
                    for t in [i / 24 * TAU for i in range(24)]]
            ctx.part(trim(f"{ctx.title} chimney band {label}", ring, 0.0075 * s, M["copper"], closed=True), chest)
        for i in range(8):
            t = i / 8 * TAU
            rivet(ctx, f"{ctx.title} chimney rivet {label}",
                  F @ Vector((math.cos(t) * 0.064 * s, math.sin(t) * 0.064 * s, 0.30 * s)), 0.0052 * s, M["copper"],
                  chest)
        rim = [F @ Vector((math.cos(t) * 0.069 * s, math.sin(t) * 0.069 * s, 0.668 * s))
               for t in [i / 32 * TAU for i in range(32)]]
        ctx.part(trim(f"{ctx.title} ember rim {label}", rim, 0.0068 * s, M["glow"], closed=True), chest)
        throat = ellipsoid(f"{ctx.title} chimney throat {label}", (0, 0, 0), (0.046 * s, 0.046 * s, 0.004 * s),
                           [M["glow"]], 16, 6)
        transform(throat, F @ Matrix.Translation((0, 0, 0.60 * s)))
        ctx.part(throat, chest)
        # 哥特尖顶垛口
        for i in range(6):
            t = i / 6 * TAU + 0.26
            b = F @ Vector((math.cos(t) * 0.078 * s, math.sin(t) * 0.078 * s, 0.640 * s))
            tip = F @ Vector((math.cos(t) * 0.090 * s, math.sin(t) * 0.090 * s, 0.745 * s))
            ctx.part(spike(f"{ctx.title} pinnacle {label}", b, tip, 0.011 * s, [M["bronze"]], sides=4), chest)
        for k, (x, y, z, sz) in enumerate(((0.012, -0.006, 0.77, 0.0065), (-0.014, 0.006, 0.88, 0.0045))):
            ctx.part(gem(f"{ctx.title} spark {label}{k}", F @ Vector((x * s, y * s, z * s)), sz * s, M["inlay"],
                         (1, 1, 1)), chest)
        # 火舌（挂 Flame.L/R，静止时藏在烟囱里，技能时沿烟囱轴升起）
        fspec = rigid(f"Flame.{label}")
        for i in range(5):
            t = i / 5 * TAU + 0.3
            b = F @ Vector((math.cos(t) * 0.021 * s, math.sin(t) * 0.021 * s, 0.42 * s))
            tip = F @ Vector((math.cos(t) * 0.009 * s, math.sin(t) * 0.009 * s, (0.640 - 0.035 * (i % 2)) * s))
            upv = F.to_3x3() @ Vector((math.cos(t), math.sin(t), 0))
            ctx.part(spike(f"{ctx.title} flame {label}{i}", b, tip, 0.017 * s, [M["flame"]], sides=6, bend=0.007 * s,
                           up=tuple(upv)), fspec)
        ctx.part(spike(f"{ctx.title} flame core {label}", F @ Vector((0, 0, 0.40 * s)), F @ Vector((0, 0, 0.655 * s)),
                       0.026 * s, [M["flame"]], sides=8), fspec)
        flames[label] = (F @ Vector((0, 0, 0.40 * s)), F @ Vector((0, 0, 0.66 * s)), axis)
    return flames


# ===== 斩刃 =====
CLEAVER = [(0.0, -0.085), (0.06, -0.100), (0.20, -0.104), (0.215, -0.090), (0.232, -0.106), (0.34, -0.108),
           (0.355, -0.094), (0.372, -0.110), (0.50, -0.114), (0.515, -0.100), (0.532, -0.116), (0.74, -0.122),
           (0.80, -0.118), (0.785, 0.020), (0.725, 0.158), (0.60, 0.160), (0.40, 0.150), (0.20, 0.132),
           (0.08, 0.110), (0.02, 0.095), (0.0, 0.080)]
CLEAVER_EDGE = [(0.03, 0.097), (0.08, 0.110), (0.20, 0.132), (0.40, 0.150), (0.60, 0.160), (0.725, 0.158),
                (0.785, 0.020), (0.80, -0.118)]


def offset_line(pts, d, centroid=(0.40, 0.02)):
    """二维折线沿法向外推 d（远离质心为外）。"""
    out = []
    for i, (x, y) in enumerate(pts):
        ax, ay = pts[max(i - 1, 0)]
        bx, by = pts[min(i + 1, len(pts) - 1)]
        tx, ty = bx - ax, by - ay
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln
        if (x - centroid[0]) * nx + (y - centroid[1]) * ny < 0:
            nx, ny = -nx, -ny
        out.append((x + nx * d, y + ny * d))
    return out


def cleaver_objs(ctx, M, origin, xa, ya, k=1.0, name="cleaver"):
    """巨型斩刃：xa 为刃尖方向，ya 为刃口方向；刃身 + 磨亮刃口 + 圣骸环 + 护手 + 缠柄 + 发光柄首。"""
    o, xa, ya = Vector(origin), Vector(xa).normalized(), Vector(ya).normalized()
    na = xa.cross(ya).normalized()
    P = lambda x, y, n=0.0: o + xa * x * k + ya * y * k + na * n * k
    objs = [plate(f"{ctx.title} {name} blade", [(x * k, y * k) for x, y in CLEAVER], 0.022 * k, [M["blade"]],
                  origin=o, xaxis=xa, yaxis=ya, bev=0.0035 * k)]
    strip = offset_line(CLEAVER_EDGE, 0.011) + list(reversed(offset_line(CLEAVER_EDGE, -0.020)))
    objs.append(plate(f"{ctx.title} {name} edge", [(x * k, y * k) for x, y in strip], 0.008 * k, [M["edge"]],
                      origin=o, xaxis=xa, yaxis=ya, bev=0.0015 * k))
    flat = [0.018 * k * (1 - 0.85 * abs(c)) for c in na]
    for sgn in (-1, 1):
        c = P(0.655, -0.050, sgn * 0.0125)
        objs.append(trim(f"{ctx.title} {name} relic ring", ring_points(c, na, 0.030 * k, 24), 0.0048 * k,
                         M["bronze"], closed=True))
        objs.append(ellipsoid(f"{ctx.title} {name} relic core", c, flat, [M["glow"]], 14, 8))
    objs.append(tube(f"{ctx.title} {name} guard", [P(-0.012, y) for y in (-0.160, -0.08, 0.01, 0.10, 0.180)],
                     [r * k for r in (0.013, 0.022, 0.025, 0.022, 0.013)], [M["bronze"]], n=10, fx=1.0, fy=0.7,
                     up=tuple(na)))
    for y in (-0.168, 0.188):
        objs.append(ellipsoid(f"{ctx.title} {name} guard knob", P(-0.012, y), (0.016 * k,) * 3, [M["bronze"]], 12, 8))
    objs.append(tube(f"{ctx.title} {name} grip", [P(-0.02, 0.0), P(-0.44, 0.0)], [0.021 * k, 0.021 * k], [M["iron"]],
                     n=12, per=1))
    for i in range(8):
        c = P(-0.06 - i * 0.048, 0.0)
        objs.append(trim(f"{ctx.title} {name} wrap", ring_points(c, xa, 0.0222 * k, 14), 0.0036 * k, M["copper"],
                         closed=True))
    pom = P(-0.472, 0.0)
    objs.append(ellipsoid(f"{ctx.title} {name} pommel", pom, (0.032 * k,) * 3, [M["bronze"]], 16, 10))
    objs.append(trim(f"{ctx.title} {name} pommel band", ring_points(pom, xa, 0.0335 * k, 20), 0.0042 * k, M["glow"],
                     closed=True))
    objs.append(spike(f"{ctx.title} {name} finial", P(-0.495, 0.0), P(-0.585, 0.0), 0.014 * k, [M["bronze"]], sides=6))
    return objs


def build_cleaver(ctx, B, M):
    """背挂巨型斩刃：刃尖朝下、刀面朝后，刀柄从两座烟囱之间升到盔顶之上。"""
    s = B.s
    chest = rigid("Chest")
    k = 1.12 * s
    origin = Vector((-0.019 * k, -0.372 * s, B.z(1.52)))
    for obj in cleaver_objs(ctx, M, origin, (0, 0, -1), (1, 0, 0), k):
        ctx.part(obj, chest)
    for x in (-0.07, 0.07):
        ctx.part(tube(f"{ctx.title} cleaver bracket", [(x * s, -0.300 * s, B.z(1.46)), (x * s, -0.362 * s, B.z(1.46))],
                      [0.011 * s, 0.011 * s], [M["bronze"]], n=8, per=1), chest)
        ctx.part(ellipsoid(f"{ctx.title} cleaver clamp", (x * s, -0.356 * s, B.z(1.46)), (0.018 * s, 0.008 * s, 0.026 * s),
                           [M["bronze"]], 12, 8), chest)


def build_blade(ctx, B, M):
    """展示页环绕用的圣骸斩刃（只进展示版；局部原点在刃中部，刃尖朝 +Y）。"""
    s = B.s
    k = 0.48 * s
    center = Vector((0.86 * s, 0.10 * s, 1.30 * s))
    origin = center - Vector((0, 0.11 * k, 0))
    blade = join(cleaver_objs(ctx, M, origin, (0, 1, 0), (1, 0, 0), k, "orbit"), f"{ctx.ID}_BLADE", center)
    # 只转节点不转网格：审图里刃尖朝上悬在身侧，网页端环绕实例只取网格（刃尖仍是局部 +Y）
    blade.rotation_euler = (math.radians(90), 0, 0)
    ctx.hidden.append(blade)


# ===== 布料 =====
def cloth(B):
    s = B.s
    return RaggedPanel("TabardF", "Pelvis", B.z(1.25), B.z(0.36), [(0, 0.30 * s), (0.5, 0.285 * s), (1.0, 0.25 * s)],
                       [(0, 0.150 * s), (0.1, 0.182 * s), (0.4, 0.200 * s), (1.0, 0.205 * s)], side=1, point=0.0,
                       joints=(0, 0.16, 0.34, 0.52, 0.74, 1.0), tails=3, tail_len=0.10 * s, seed=2.2)


def build(ctx):
    M = materials(ctx)
    B = Body(height=2.0, shoulder=0.25, bulk=1.25, chest=1.15, waist=1.10, hips=1.12, limb=1.18, arm_out=0.68,
             stance=1.25)
    s = B.s
    suit_torso_uv(ctx, B, M["mail"])
    for side, label in SIDES:
        suit_arm_uv(ctx, B, side, label, M["mail"])
        suit_leg_uv(ctx, B, side, label, M["mail"])
        hand(ctx, B, side, label, M["iron"], glow=M["glow"], scale=1.5)
    build_cuirass(ctx, B, M)
    doors = build_furnace(ctx, B, M)
    gorget_lite(ctx, B, M["iron"], M["bronze"], layers=((1.640, 1.700, 0.128, 0.098), (1.690, 1.748, 0.100, 0.078)),
                nu=44, trim_r=0.0030)
    build_waist(ctx, B, M)
    build_arms(ctx, B, M)
    build_legs(ctx, B, M)
    hc = build_helm(ctx, B, M)
    flames = build_back(ctx, B, M)
    build_cleaver(ctx, B, M)
    build_blade(ctx, B, M)
    front = cloth(B)
    front.build(ctx, [M["tabard"], M["lining"]], f"{ctx.title} tabard", nu=22, nv=48, edges=(M["bronze"], 0.0035 * s))
    front.hem(ctx, f"{ctx.title} tabard", M["hem"], 0.0032 * s)
    ensure_uv(ctx)
    tri_report(ctx)
    return {"B": B, "front": front, "hc": hc, "doors": doors, "flames": flames}


def skeleton(rig, st):
    B = st["B"]
    add_skeleton(rig, B)
    for label, (h, t) in st["doors"].items():
        rig.bone(f"Door.{label}", h, t, "Chest", roll=Y)
    for label, (h, t, _) in st["flames"].items():
        rig.bone(f"Flame.{label}", h, t, "Chest", roll=Y)
        rig.translate[f"Flame.{label}"] = f"_flame{label}"
    rig.add_garment(st["front"])


# ===== 动作 =====
REVIEW_POSE = ("Idle", 1)


def flames(st, pose, amount):
    """火舌沿烟囱轴升起 amount 米（0 为藏在烟囱里）。"""
    for label, (_, _, axis) in st["flames"].items():
        pose[f"_flame{label}"] = axis * amount * st["B"].s


def idle_pose(rig, st, t):
    B = st["B"]
    p = idle(rig, B, t, breathe=0.026, sway=0.010, arms=0.02, spread=0.03, bend=0.18)
    # 重装待机：重心更低、膝微屈；双臂被肩甲与护手撑开
    p["_hover"] = -0.028 * B.s + 0.006 * B.s * math.sin(2 * t)
    Legs(rig, B).stand(p, 0.03 * B.s, 0.18)
    for label, sg in (("L", -1), ("R", 1)):
        p[f"UpperArm.{label}"] = R((Y, sg * (0.14 + 0.02 * math.sin(t + 0.5 * sg))), (X, 0.06 + 0.025 * math.sin(t + 1)))
        p[f"Forearm.{label}"] = R((X, 0.32 + 0.04 * math.sin(t + 1.4)))
        fingers(p, B, label, lambda i: 0.55 + 0.05 * math.sin(2 * t + i * 0.6))
    flames(st, p, 0.0)
    rig.garment_pose(p, st["front"], lambda k, j: 0.04 + 0.015 * math.sin(t + j * 0.8))
    return p


def move_pose(rig, st, t):
    B = st["B"]
    p = gait(rig, B, t, stride=0.42, lift=0.13, stance=0.5, bob=0.045, lean=0.12, twist=0.06, arm=0.35, elbow=0.80,
             arm_in=0.14, width=0.04, sink=0.07, heel=0.04, knee_out=0.16, sway=0.018, phase_bob=math.pi)
    stomp = max(0.0, math.cos(2 * t)) ** 6          # 落脚瞬间胸口顿挫
    p["Chest"] = R((X, -0.035 * stomp)) @ p["Chest"]
    p["Head"] = R((X, 0.02 * stomp)) @ p["Head"]
    for label in ("L", "R"):
        fingers(p, B, label, 0.95)
    flames(st, p, 0.0)
    panel_clear(rig, B, p, st["front"], 0.03 * math.sin(2 * t + 0.5), margin=0.10)
    return p


def cast_key(rig, st, stage):
    """断层：蓄力（双拳高举）→ 砸地（深蹲前扑、双拳合握砸向脚前）→ 余震保持 → 收势。"""
    B = st["B"]
    s = B.s
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    if stage == 1:
        p["Pelvis"] = R((X, 0.03))
        p["Spine"] = R((X, 0.06))
        p["Chest"] = R((X, 0.08))
        p["Neck"] = R((X, 0.06))
        p["Head"] = R((X, 0.10))
        plant_stance(rig, B, p, (-0.05, 0.10), (0.05, -0.10), 0.03, 0.15, -0.15, knee_out=0.25)
        for label, sd in (("L", -1), ("R", 1)):
            arm_ik(rig, p, label, (sd * 0.080 * s, 0.24 * s, B.z(2.22)), (sd * 1.0, -0.4, 0.2),
                   hand_dir=(-sd * 0.15, 0.35, 1.0))
            fingers(p, B, label, 1.3)
        flames(st, p, 0.03)
    else:
        follow = stage == 3
        p["Pelvis"] = R((X, -0.36 if not follow else -0.30))
        p["Spine"] = R((X, -0.30 if not follow else -0.24))
        p["Chest"] = R((X, -0.24 if not follow else -0.18))
        p["Neck"] = R((X, 0.26))
        p["Head"] = R((X, 0.30))
        plant_stance(rig, B, p, (-0.08, 0.12), (0.08, -0.10), 0.32 if not follow else 0.28, 0.25, -0.25, knee_out=0.38)
        tz = 0.26 if not follow else 0.32
        for label, sd in (("L", -1), ("R", 1)):
            arm_ik(rig, p, label, (sd * 0.07 * s, 0.62 * s, B.z(tz)), (sd * 1.0, -0.6, 0.4),
                   hand_dir=(sd * 0.1, 0.4, -1.0))
            fingers(p, B, label, 1.35)
        flames(st, p, 0.12 if not follow else 0.08)
    panel_clear(rig, B, p, st["front"], margin=0.10)
    return p


def channel_key(rig, st, stage):
    """烈日处决：双臂 V 形高举、仰首、马步，炉门洞开、烟囱喷火。"""
    B = st["B"]
    s = B.s
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    p["Pelvis"] = R((X, 0.02))
    p["Spine"] = R((X, 0.05))
    p["Chest"] = R((X, 0.08))
    p["Neck"] = R((X, 0.06))
    p["Head"] = R((X, 0.16))
    plant_stance(rig, B, p, (-0.12, 0.02), (0.12, -0.02), 0.12, 0.30, -0.30, knee_out=0.35)
    for label, sd in (("L", -1), ("R", 1)):
        arm_ik(rig, p, label, (sd * 0.62 * s, 0.22 * s, B.z(2.20)), (sd * 0.3, -1.0, -0.3),
               hand_dir=(sd * 0.5, 0.2, 1.0))
        fingers(p, B, label, lambda i: 0.2 if i == 0 else -0.08, spread=1.0)
    p["Door.L"] = R((Z, 1.35))
    p["Door.R"] = R((Z, -1.35))
    flames(st, p, 0.17)
    panel_clear(rig, B, p, st["front"], 0.04, margin=0.10)
    return p


def animate(rig, st):
    rig.loop("Idle", 72, lambda t: idle_pose(rig, st, t))
    rig.loop("Move", 20, lambda t: move_pose(rig, st, t), step=1)
    k = [cast_key(rig, st, i) for i in range(4)]
    rig.keyed("Cast", [(1, k[0]), (8, k[1]), (14, k[2]), (20, k[3]), (32, k[0])])
    c = [channel_key(rig, st, i) for i in range(2)]
    rig.keyed("Channel", [(1, c[0]), (13, c[1]), (28, c[1]), (42, c[0])])
