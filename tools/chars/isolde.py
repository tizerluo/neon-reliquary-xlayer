"""伊索尔德 · 寒霜执行官（Isolde, The Frost Executor）——第三轮：加体量、真浮雕甲面、滑冰重心、贴身武器。

设定：在冰面上滑行的纤长处刑者。冰白漆甲 + 浓郁深海军蓝长大衣（下摆向上生长的发光霜花、暗纹织锦）+ 银色滚边，
玻璃质冰晶（根部内发光、尖端近白）只占小面积。
标志件：流线头盔 + 黑冰处刑面甲 + V 形冷光眼缝 + 冰棱王冠；五片叠压的大肩甲，甲缝里长出冰晶，肩头与背后的冰晶簇
（Channel 时外张）；斜背在背后的冰晶处刑大剑（刚性挂 Chest）；高立领及小腿的分叉长大衣 + 身后两条拖到脚踝的燕尾
（滑行时随风后扬并自动让开双腿）。
体量（第三轮）：Body 加粗（躯干 / 骨盆 / 四肢），躯干双层胸甲（V 形凸棱 + 下缘冰棱）+ 三道腹甲 + 三片前腹甲；
大腿三片叠压（尖角下缘、凸棱、浮雕霜纹）、冰晶护膝、三片护胫；上臂两片臂甲 + 护肘冰晶 + 两片护臂（喇叭腕口）+ 护手；
放样铁靴 + 四片脚背甲 + 冰刃。所有甲片带单段倒角，银滚边为 3 边细管，面数从源头控制。
动作：Idle（丁字站姿）/ Move（花样滑冰式长滑步：重心随蹬冰横移并深蹲、躯干前倾约 20°、髋肩反向拧转、蹬冰腿侧后伸展、
双臂连续一前一后）/ Cast（寒霜领域：深弓步 + 右臂自左肩蓄力横扫、左臂后展平衡）/ Channel（绝对零度：右臂擎天、左掌下压、
冰晶外张，13–28 帧保持）。
网页端节点：ISOLDE_BLADE（展示页环绕的冰晶刃，只进展示版；位置贴近右髋，审图不渲染它）。
"""

import math
import os

from mathutils import Matrix, Vector

from kit.core import (TAU, apply_all, clamp, finish, gem, interp, invdist, join, lerp, orient, plate, projector,
                      radial, rigid, smoothstep, solidify, surface, trim, tube)
from kit.garment import Wrap
from kit.humanoid import (SIDES, Body, add_skeleton, hand, sabaton, suit_arm, suit_leg, suit_torso, vambrace)
from kit.motion import Legs, fingers, idle
from kit.rig import I3, R, X, Y, Z

from chars._grace_helpers import (Clearance, cloth_edges, frost_hem_maps, gorget2, hem_line, keyed_samples,
                                  mat_slerp, pauldron2, radial_wrap)
from chars._isolde2_kit import (band, blade_maps, brocade_maps, coat_clear, crystal2, crystal_maps,
                                executioner_sword, frost_plate_maps, shell2)
from chars._isolde3_kit import (arm_armor3, band3, boot3, coat_maps, fern, gauntlet3, icicle_fringe, lacquer_maps, leg_armor3, shell3,
                                skate3, suit_arm2, suit_leg2, suit_torso2, torso_plates3)

TITLE = "Isolde"
ACCENT = (0.61, 0.93, 0.98)
CLIPS = ("Idle", "Move", "Cast", "Channel")
GAME_TRIS = 64000
LOD_KEEP = ("inlay", "glow", "hem", "trim", "core", "crystal")
REVIEW_POSE = ("Idle", 1)
ICE = ACCENT
J5 = (0, 0.16, 0.34, 0.52, 0.74, 1.0)


def materials(ctx):
    M = ctx.M
    # 冰白漆甲：低金属度的漆面 + 清漆，雕花沟槽压成深钢蓝，远看也能读出霜纹
    white = (0.70, 0.78, 0.86)
    ctx.mat("plate", "ice-white lacquer plate", white, metal=0.08, rough=0.30, coat=1.0, spec=0.55)
    ctx.texture("plate", lacquer_maps((0.66, 0.75, 0.85), (0.46, 0.60, 0.77), (0.88, 0.93, 0.98), (0.14, 0.25, 0.43), ICE,
                                      size=2048, seed=31), emit_strength=3.0, normal_strength=1.0)
    enamel = (0.62, 0.72, 0.82)
    ctx.mat("enamel", "ice-white enamel helm", enamel, metal=0.08, rough=0.24, coat=1.0, spec=0.6)
    ctx.texture("enamel", frost_plate_maps(enamel, (0.34, 0.45, 0.58), size=1024, seed=57, cells=6, width=3),
                normal_strength=0.8)
    ctx.mat("silver", "silver trim", (0.86, 0.89, 0.94), metal=1.0, rough=0.16)
    ctx.mat("steel", "frost silver", (0.72, 0.77, 0.85), metal=1.0, rough=0.26)
    # 浓郁深海军蓝（线性空间偏蓝紫，避免发灰发绿），光泽取冷蓝
    navy = (0.011, 0.028, 0.135)
    ctx.mat("coat", "deep navy frost coat", navy, rough=0.68, sheen=0.10, sheen_tint=(0.40, 0.55, 1.0), spec=0.15)
    ctx.texture("coat", coat_maps(ICE, navy, (0.050, 0.100, 0.250), size=2048, seed=9), emit_strength=2.0,
                normal_strength=0.6)
    ctx.mat("brocade", "navy brocade coat", navy, rough=0.62, sheen=0.12, sheen_tint=(0.40, 0.55, 1.0), spec=0.18)
    ctx.texture("brocade", brocade_maps(navy, (0.12, 0.20, 0.42), size=1024, seed=5, cells=16), normal_strength=0.5)
    ctx.mat("lining", "ice blue lining", (0.030, 0.120, 0.260), rough=0.4, sheen=0.4, sheen_tint=(0.6, 0.85, 1))
    ctx.mat("suit", "navy undersuit", (0.006, 0.012, 0.042), metal=0.1, rough=0.55, sheen=0.12,
            sheen_tint=(0.5, 0.7, 1.0))
    ctx.mat("crystal", "ice crystal", (0.40, 0.72, 0.88), rough=0.04, emit=ICE, strength=1.0, coat=1.0, spec=0.9)
    ctx.texture("crystal", crystal_maps(ICE), emit_strength=3.0, normal_strength=0.4)
    ctx.mat("visor", "black ice visor", (0.004, 0.012, 0.018), metal=0.1, rough=0.05, coat=1.0, spec=0.8)
    ctx.mat("glow", "ice core glow", (0.6, 0.9, 1.0), emit=ICE, strength=8.0)
    ctx.mat("inlay", "ice circuit inlay", (0.35, 0.60, 0.65), emit=ICE, strength=5.5)
    ctx.mat("hem", "ice hem light", (0.30, 0.50, 0.55), emit=ICE, strength=7.0)
    ctx.mat("blade", "glacier blade crystal", (0.35, 0.65, 0.78), metal=0.1, rough=0.05, emit=ICE, strength=1.0,
            coat=1.0, spec=0.9)
    ctx.texture("blade", blade_maps(ICE, deep=(0.02, 0.09, 0.22), pale=(0.40, 0.66, 0.84)), emit_strength=1.5,
                normal_strength=0.4)
    return M


# ===== 头盔、眼缝与冰棱王冠 =====
def build_helm(ctx, B, M):
    s = B.s
    hc = Vector((0, 0.010 * s, B.z(1.878)))
    rx, ry = 0.086 * s, 0.102 * s
    prof = [(0.0, (0.00, 0.126)), (0.08, (0.42, 0.120)), (0.22, (0.75, 0.098)), (0.40, (0.94, 0.056)),
            (0.55, (1.00, 0.010)), (0.70, (0.95, -0.040)), (0.84, (0.80, -0.086)), (1.0, (0.62, -0.116))]
    eye_z = hc.z + 0.006 * s

    def vz(x):
        return eye_z + 0.013 * s * min(1.0, abs(x) / (0.050 * s)) ** 1.2

    def hp(u, v):
        a = u * TAU
        r, dz = interp(prof, v)
        front, back = max(0.0, math.cos(a)), max(0.0, -math.cos(a))
        x = rx * r * math.sin(a)
        y = ry * r * math.cos(a)
        z = hc.z + dz * s
        rake = 0.062 * s * back ** 2 * smoothstep(0.04, 0.45, v) * (1 - smoothstep(0.55, 0.92, v))   # 后脑流线尾
        prow = 0.018 * s * math.exp(-(x / (0.020 * s)) ** 2) * front ** 2 * smoothstep(0.30, 0.9, v)
        groove = 0.0
        if front > 0.3:
            groove = -0.004 * s * math.exp(-((z - vz(x)) / (0.0060 * s)) ** 2) * (1 - smoothstep(0.050 * s, 0.062 * s, abs(x)))
        cheek = -0.007 * s * front * smoothstep(0.66, 0.95, v) * math.exp(-((abs(x) - 0.048 * s) / (0.018 * s)) ** 2)
        return Vector((x, y + hc.y + prow + (groove + cheek) * front - rake, z))
    helm = surface(f"{ctx.title} helm", hp, 56, 34, [M["enamel"]])
    orient(helm, lambda c: hc)
    helm = finish(helm, 0.006 * s, -1, 0)
    ctx.part(helm, rigid("Head"))
    proj = projector(helm, (0, -1, 0))
    # 黑冰处刑面甲：从眉线下方盖到下颌、向下收成尖颏的盾形，远看在白盔上读出一张冷峻的“脸”
    chin_z = hc.z - 0.102 * s

    def fp(u, v):
        w = 0.064 * s * (1 - 0.76 * v ** 1.3)
        x = (2 * u - 1) * w
        return proj(Vector((x, 1.0, lerp(vz(x) + 0.0155 * s, chin_z, v))), 0.0016 * s)
    face = surface(f"{ctx.title} faceplate", fp, 26, 16, [M["visor"]])
    orient(face, lambda c: hc)
    ctx.part(finish(face, 0.0024 * s, -1, 0), rigid("Head"))
    rim = ([fp(i / 20, 0.0) for i in range(21)] + [fp(1.0, j / 10) for j in range(1, 11)]
           + [fp(1 - i / 8, 1.0) for i in range(1, 8)] + [fp(0.0, 1 - j / 10) for j in range(0, 10)])
    ctx.part(trim(f"{ctx.title} faceplate rim", rim, 0.0026 * s, M["silver"], closed=True, n=3), rigid("Head"))
    # V 形冷光眼缝（中间低、两端上挑，读作冷峻的处刑者目光）嵌在面甲上；管截面 fx 沿竖直、fy 沿前后
    xs = [(i / 20 * 2 - 1) * 0.056 * s for i in range(21)]
    slit = [proj(Vector((x, 1.0, vz(x))), 0.0034 * s) for x in xs[1:-1]]
    ctx.part(tube(f"{ctx.title} visor slit", slit, [0.0050 * s] * 19, [M["glow"]], n=6, fx=0.62, fy=1.0,
                  up=(0, 0, 1), per=2), rigid("Head"))
    # 面甲口鼻处三道竖向冷光通风缝
    for k, x in enumerate((-0.012, 0.0, 0.012)):
        vent = [proj(Vector((x * s, 1.0, eye_z - 0.050 * s - i * 0.0055 * s)), 0.0034 * s) for i in range(6)]
        ctx.part(tube(f"{ctx.title} vent {k}", vent, [0.0015 * s] * 6, [M["inlay"]], n=3), rigid("Head"))
    # 银额箍与颈沿
    band_z = lambda a: eye_z + 0.034 * s + 0.010 * s * (1 - math.cos(a)) / 2
    hit = radial_wrap([helm], (0, hc.y, 0))
    ring = [hit(i / 72 * TAU, band_z(i / 72 * TAU), 0.003 * s) for i in range(72)]
    ctx.part(trim(f"{ctx.title} circlet", ring, 0.0045 * s, M["silver"], closed=True, n=6), rigid("Head"))
    rim = [radial(hp(i / 72, 1.0), 0.004 * s, hc.y) for i in range(72)]
    ctx.part(trim(f"{ctx.title} helm rim", rim, 0.0036 * s, M["silver"], closed=True, n=3), rigid("Head"))
    # 顶脊：一道银色细脊从额心越过盔顶顺着流线尾收尖，两侧各一道冷光嵌线
    crest = [hp(0.0, v) for v in [0.46 - i / 16 * 0.46 for i in range(17)]]
    crest += [hp(0.5, v) for v in [i / 16 * 0.70 for i in range(17)]][1:]
    crest = [p + (p - hc).normalized() * 0.0035 * s for p in crest]
    ctx.part(trim(f"{ctx.title} helm crest", crest, 0.0032 * s, M["silver"], n=3), rigid("Head"))
    for sd in (-1, 1):
        line = [hp(sd * 0.075 % 1.0, v) for v in [0.10 + i / 12 * 0.40 for i in range(13)]]
        line = [p + (p - hc).normalized() * 0.002 * s for p in line]
        ctx.part(trim(f"{ctx.title} helm inlay {sd}", line, 0.0017 * s, M["inlay"], n=3), rigid("Head"))
    # 冰棱王冠：额箍前半圈长出参差修长的刻面冰棱，正中一柄最高，两侧成对递减并外倾成扇，向后渐短
    spec = [(0.0, 0.340, 0.027)]
    for a, L, r in ((0.30, 0.150, 0.014), (0.50, 0.250, 0.021), (0.72, 0.120, 0.013), (0.92, 0.190, 0.018),
                    (1.16, 0.100, 0.012), (1.40, 0.135, 0.014), (1.85, 0.070, 0.010), (2.35, 0.050, 0.008)):
        spec += [(-a, L, r), (a, L, r)]
    for k, (a, L, r) in enumerate(spec):
        base = hit(a, band_z(a) + 0.002 * s, 0.001 * s)
        out = Vector((math.sin(a), math.cos(a), 0))
        el = math.radians(88 - 30 * min(1.0, abs(a) / 1.5))
        d = (out * math.cos(el) + Vector((0, 0, 1)) * math.sin(el) - Vector((0, 0.12, 0)) * (1 - abs(a) / 2.6))
        d.normalize()
        ctx.part(crystal2(f"{ctx.title} icicle {k}", base - d * 0.008 * s, base + d * L * s, r * s, [M["crystal"]],
                          sides=6 if L > 0.15 else 5, shoulder=0.66, foot=0.55, seed=k * 1.7, twist=k * 0.4),
                 rigid("Head"))
    ctx.part(gem(f"{ctx.title} brow gem", hit(0.0, band_z(0.0) - 0.006 * s, 0.006 * s), 0.011 * s, M["glow"],
                 (0.8, 0.5, 1.4)), rigid("Head"))
    for sd in (-1, 1):
        ctx.part(gem(f"{ctx.title} crown gem {sd}", hit(sd * 0.36, band_z(sd * 0.36), 0.005 * s), 0.007 * s,
                     M["glow"], (0.8, 0.5, 1.2)), rigid("Head"))
    return hc


# ===== 胸甲霜星、高立领 =====
def build_emblem(ctx, B, M, cuirass):
    s = B.s
    proj = projector(cuirass, (0, -1, 0))
    c = proj(Vector((0, 1.0, B.z(1.560))), 0.0)
    ctx.part(crystal2(f"{ctx.title} heart crystal", c - Vector((0, 0.006 * s, 0.036 * s)),
                      c + Vector((0, 0.006 * s, 0.040 * s)), 0.021 * s, [M["crystal"]], sides=6, shoulder=0.55,
                      foot=0.05), rigid("Chest"))
    ctx.part(gem(f"{ctx.title} heart glow", c + Vector((0, 0.004 * s, 0)), 0.010 * s, M["glow"], (0.8, 0.6, 1.4)),
             rigid("Chest"))
    # 银色六角框托住心晶
    hexa = [proj(Vector((math.sin(k / 6 * TAU + math.pi / 6) * 0.036 * s, 1.0,
                         c.z + math.cos(k / 6 * TAU + math.pi / 6) * 0.046 * s)), 0.003 * s) for k in range(6)]
    ctx.part(trim(f"{ctx.title} heart frame", hexa, 0.0032 * s, M["silver"], closed=True, n=3), rigid("Chest"))
    # 六臂霜星嵌线：主臂更长更粗，带两对 60° 分枝，末端落光点
    for k in range(6):
        a = k / 6 * TAU
        main = [proj(Vector((math.sin(a) * r * s, 1.0, c.z + math.cos(a) * r * s)), 0.0024 * s)
                for r in [0.046 + i * 0.008 for i in range(8)]]
        main = [p for p in main if p.y < 0.9]
        if len(main) < 3:
            continue
        # 凸起的银色主臂（浮雕）+ 骑在上面的冷光嵌线
        ctx.part(tube(f"{ctx.title} frost star rib {k}", main, [0.0058 * s - 0.0003 * s * i for i in range(len(main))],
                      [M["silver"]], n=3, per=1), rigid("Chest"))
        ctx.part(trim(f"{ctx.title} frost star {k}", [p + Vector((0, 0.0042 * s, 0)) for p in main], 0.0022 * s,
                      M["inlay"], n=3), rigid("Chest"))
        ctx.part(gem(f"{ctx.title} frost star tip {k}", main[-1], 0.0042 * s, M["glow"], (1, 0.6, 1)), rigid("Chest"))
        for f, L in ((0.40, 0.026), (0.72, 0.018)):
            r0 = 0.046 + f * 0.056
            for sd in (-1, 1):
                b = a + sd * math.pi / 3
                br = [proj(Vector((math.sin(a) * r0 * s + math.sin(b) * t * s, 1.0,
                                   c.z + math.cos(a) * r0 * s + math.cos(b) * t * s)), 0.0024 * s)
                      for t in (0.0, L * 0.5, L)]
                if all(p.y < 0.9 for p in br):
                    ctx.part(trim(f"{ctx.title} frost twig {k}{f}{sd}", br, 0.0016 * s, M["inlay"], n=3),
                             rigid("Chest"))


def build_collar(ctx, B, M):
    """高立领：包住后颈与两侧、向上外翻，外为深蓝织锦、内为冰蓝衬里，银沿 + 冷光嵌线。"""
    s = B.s

    def cp(u, v):
        a = math.pi - 1.85 + u * 3.70
        side = abs(math.cos(a)) if math.cos(a) > 0 else 0.0     # 0 在后半圈，越靠前越大
        top = lerp(B.z(1.815), B.z(1.735), side ** 1.2 + 0.25 * abs(math.sin(a)) ** 4)
        z = lerp(B.z(1.650), top, v)
        r = lerp(0.108, 0.146, v ** 1.4) * s
        return Vector((r * math.sin(a) * 1.05, r * math.cos(a) * 0.95 - 0.008 * s, z))
    col = surface(f"{ctx.title} collar", cp, 40, 8, [M["brocade"], M["lining"]], uvfn=lambda u, v: (u * 1.2, v * 0.4))
    orient(col, lambda c: Vector((0, 0, c.z)))
    solidify(col, 0.006 * s, 0, inner_offset=1)
    ctx.part(apply_all(col), rigid("Chest"))
    ctx.part(trim(f"{ctx.title} collar rim", [cp(i / 44, 1.0) for i in range(45)], 0.0036 * s, M["silver"], n=3),
             rigid("Chest"))
    for u in (0.0, 1.0):
        ctx.part(trim(f"{ctx.title} collar edge {u}", [cp(u, j / 8) for j in range(9)], 0.0030 * s, M["silver"], n=3),
                 rigid("Chest"))
    for vv in (0.55, 0.80):
        line = [cp(i / 40, vv) + (cp(i / 40, vv) - Vector((0, 0, cp(i / 40, vv).z))).normalized() * 0.004 * s
                for i in range(2, 39)]
        ctx.part(trim(f"{ctx.title} collar inlay {vv}", line, 0.0016 * s, M["inlay"], n=3), rigid("Chest"))


# ===== 冰晶簇（肩头挂 Frost.L/R，背后挂 FrostBack，Channel 时外张） =====
def cluster(ctx, M, bone, base, main, spread, sizes, clear, tag, seed=0.0):
    """在 base 附近长出一簇冰晶：main 为主方向，spread 为发散角，sizes 为 [(长, 半径), ...]（首枚为主晶）。"""
    main = Vector(main).normalized()
    u = main.orthogonal().normalized()
    w = main.cross(u)
    for k, (L, r) in enumerate(sizes):
        ang = (k * 2.39996 + seed) % TAU                  # 黄金角分布
        f = 0.0 if k == 0 else spread * (0.45 + 0.55 * ((k * 0.618 + seed * 0.3) % 1.0))
        d = (main * math.cos(f) + (u * math.cos(ang) + w * math.sin(ang)) * math.sin(f)).normalized()
        off = (u * math.cos(ang + 1.3) + w * math.sin(ang + 1.3)) * r * (0.0 if k == 0 else 1.1)
        b = Vector(base) + off - d * r * 0.8
        ctx.part(crystal2(f"{ctx.title} {tag} crystal {k}", b, b + d * L, r, [M["crystal"]], sides=6 if k % 3 else 5,
                          shoulder=0.68 + 0.08 * math.sin(k), foot=0.66, seed=k + seed, twist=k * 0.7,
                          lean=0.25 * math.sin(k * 1.9)), rigid(bone))
        clear.point(bone, b + d * L, f"{tag} crystal tip")
        clear.point(bone, b + d * L * 0.55, f"{tag} crystal mid")


def build_crystals(ctx, B, M, clear):
    s = B.s
    for side, label in SIDES:
        sh = B.arms[label]["shoulder"]
        base = sh + Vector((side * 0.020 * s, -0.040 * s, 0.128 * s))
        cluster(ctx, M, f"Frost.{label}", base, (side * 0.50, -0.40, 0.78), 0.58,
                [(k[0] * s, k[1] * s) for k in ((0.330, 0.027), (0.250, 0.023), (0.205, 0.020), (0.170, 0.018),
                                                (0.140, 0.016), (0.112, 0.014), (0.090, 0.012), (0.070, 0.010),
                                                (0.055, 0.009), (0.042, 0.008))],
                clear, f"shoulder {label}", seed=1.3 if side > 0 else 2.9)
        ctx.part(gem(f"{ctx.title} shoulder core {label}", base - Vector((0, 0, 0.004 * s)), 0.014 * s, M["glow"],
                     (1, 1, 0.7)), rigid(f"Frost.{label}"))
    # 背后两扇冰晶：从斜背大剑两侧的背甲里迸出，右上一扇更高、左下一扇向外横展
    for tag, x, z, main, sizes, seed in (
            ("back R", 0.090, 1.565, (0.56, -0.50, 0.66),
             ((0.48, 0.033), (0.38, 0.029), (0.33, 0.026), (0.27, 0.023), (0.22, 0.020), (0.17, 0.016),
              (0.13, 0.013), (0.095, 0.011), (0.07, 0.009)), 0.7),
            ("back L", -0.100, 1.450, (-0.45, -0.55, 0.70),
             ((0.40, 0.030), (0.33, 0.027), (0.28, 0.024), (0.22, 0.020), (0.17, 0.016), (0.13, 0.013),
              (0.095, 0.011), (0.07, 0.009)), 2.1)):
        b = B.on_torso(x * s, B.z(z), 0.030 * s, back=True)
        cluster(ctx, M, "FrostBack", b, main, 0.42, [(L * s, r * s) for L, r in sizes], clear, tag, seed=seed)
        ctx.part(gem(f"{ctx.title} {tag} core", b + Vector((0, -0.008 * s, 0)), 0.016 * s, M["glow"], (1, 0.6, 1)),
                 rigid("FrostBack"))


# ===== 冰刃靴 =====
def build_skate(ctx, B, M, side, label):
    s = B.s
    L = B.legs[label]
    ankle, toe = L["ankle"], L["toe"]
    x = (ankle.x + L["ball"].x) / 2
    top, bot = B.hover + 0.004 * s, 0.004 * s
    hy, ty = ankle.y - 0.058 * s, toe.y + 0.040 * s
    outline = [(hy, top), (hy + 0.004 * s, bot + 0.014 * s), (hy + 0.030 * s, bot), (ty - 0.060 * s, bot),
               (ty - 0.022 * s, bot + 0.008 * s), (ty, bot + 0.030 * s), (ty - 0.004 * s, top - 0.006 * s),
               (ty - 0.050 * s, top)]
    spec = rigid(f"Foot.{label}")
    ctx.part(plate(f"{ctx.title} skate blade {label}", outline, 0.0060 * s, [M["crystal"]], origin=(x, 0, 0),
                   xaxis=(0, 1, 0), yaxis=(0, 0, 1), bev=0.0012 * s), spec)
    edge = [Vector((x, hy + 0.030 * s, bot + 0.0015 * s)), Vector((x, ty - 0.060 * s, bot + 0.0015 * s)),
            Vector((x, ty - 0.022 * s, bot + 0.0095 * s)), Vector((x, ty - 0.002 * s, bot + 0.029 * s))]
    ctx.part(trim(f"{ctx.title} skate edge {label}", edge, 0.0018 * s, M["glow"], n=3), spec)
    for yy in (hy + 0.020 * s, ty - 0.070 * s):
        ctx.part(tube(f"{ctx.title} skate post {label}{yy:.2f}", [(x, yy, top + 0.010 * s), (x, yy, bot + 0.018 * s)],
                      [0.0065 * s, 0.0045 * s], [M["steel"]], n=8, per=1), spec)
    ctx.part(tube(f"{ctx.title} skate rail {label}", [(x, hy + 0.01 * s, top + 0.002 * s),
                                                     (x, ty - 0.03 * s, top + 0.002 * s)],
                  [0.0060 * s, 0.0055 * s], [M["steel"]], n=8, per=1), spec)


def build_blade(ctx, B, M):
    """展示页环绕用的冰晶刃（游戏内由原生飞剑绘制，不进 LOD）。"""
    s = B.s
    core = crystal2(f"{ctx.title} glacier blade", (0, -0.02 * s, 0), (0, 0.52 * s, 0), 0.034 * s, [M["blade"]],
                    sides=6, shoulder=0.80, foot=0.9, twist=math.pi / 6)
    core.data.transform(Matrix.Scale(0.34, 4, (0, 0, 1)))
    objs = [core]
    for sd in (-1, 1):
        objs.append(trim(f"{ctx.title} glacier fuller {sd}", [(0, 0.03 * s, sd * 0.0058 * s), (0, 0.36 * s, sd * 0.0042 * s)],
                         0.0018 * s, M["glow"]))
    guard = [Vector((math.sin(t) * 0.075 * s, -0.035 * s + 0.018 * s * math.cos(t) ** 2, 0)) for t in
             [(-1.2 + i * 2.4 / 16) for i in range(17)]]
    objs.append(tube(f"{ctx.title} glacier guard", guard, [0.004 * s] + [0.0075 * s] * 15 + [0.004 * s], [M["steel"]],
                     n=8))
    for sd in (-1, 1):
        objs.append(crystal2(f"{ctx.title} guard shard {sd}", (sd * 0.07 * s, -0.03 * s, 0),
                             (sd * 0.115 * s, 0.02 * s, 0), 0.010 * s, [M["blade"]], sides=5))
    objs.append(tube(f"{ctx.title} glacier grip", [(0, -0.04 * s, 0), (0, -0.10 * s, 0), (0, -0.15 * s, 0)],
                     [0.010 * s, 0.009 * s, 0.010 * s], [M["coat"]], n=10))
    objs.append(gem(f"{ctx.title} glacier pommel", (0, -0.165 * s, 0), 0.014 * s, M["glow"], (1, 1.2, 1)))
    # 网页端按子网格的局部几何实例化环绕：顶点必须围绕局部原点、刃尖朝 +Y，所以合并时不做世界位移补偿
    blade = join(objs, f"{ctx.ID}_BLADE")
    blade.data.transform(Matrix.Scale(0.80, 4))      # 展示用环绕刃缩小，并贴近身侧（上一轮悬在 0.8 m 外，读作“悬浮法杖”）
    blade.location = Vector((0.50, -0.12, 1.14)) * s
    blade.hide_render = True        # 审图不渲染（贴身的展示用环绕节点会被读成“悬浮法杖”），但仍随展示版 GLB 导出
    ctx.hidden.append(blade)


# ===== 长大衣：及小腿的分叉前摆 + 身后两条拖到脚踝的燕尾 =====
COAT_A0 = 0.60


def coat_wrap(B):
    s = B.s
    top, hipz = B.z(1.262), B.z(1.02)
    a0, a1 = COAT_A0, TAU - COAT_A0

    def bottom(u):
        a = a0 + u * (a1 - a0)
        d = abs(a - math.pi)                               # 离后中线的角距
        base = B.z(0.36) - 0.025 * s * (math.exp(-((a - a0) / 0.14) ** 2) + math.exp(-((a1 - a) / 0.14) ** 2))
        tip_z, notch_z, tip_a = B.z(0.085), B.z(0.60), 0.44
        if d < tip_a:                                      # 燕尾内缘：后中开衩直线收到尾尖
            return lerp(notch_z, tip_z, (d / tip_a) ** 1.15)
        return lerp(base, tip_z, math.exp(-((d - tip_a) / 0.50) ** 2))   # 燕尾外缘弧线过渡到侧摆

    def radius(u, v, a):
        z = lerp(top, bottom(u), v)
        h1 = smoothstep(top, hipz, z)
        t2 = clamp((hipz - z) / (hipz - B.z(0.08))) ** 1.05
        return (0.184 + 0.066 * h1 + 0.135 * t2) * s, (0.146 + 0.058 * h1 + 0.105 * t2) * s
    return Wrap("Coat", "Pelvis", a0, a1, top=top, bottom=bottom, r_top=None, r_bot=None, K=8, joints=J5, cy=0.0,
                flow=0.030 * s, widen=0.03, folds=(7.0, 0.003 * s, 0.018 * s), seed=2.2, radius_fn=radius)


# ===== 构建 =====
def build(ctx):
    M = materials(ctx)
    B = Body(height=2.0, shoulder=0.225, bulk=1.12, chest=1.08, waist=0.98, hips=1.12, limb=1.16, hover=0.058,
             female=True, stance=1.12)
    s = B.s
    T = ctx.title
    clear = Clearance2()
    suit_torso2(ctx, B, M["suit"])
    for side, label in SIDES:
        suit_arm2(ctx, B, label, M["suit"])
        suit_leg2(ctx, B, label, M["suit"])
        h = hand(ctx, B, side, label, M["plate"], glow=M["glow"], scale=1.22, finger_r=0.0125, claw=(M["crystal"], 0.020))
        gauntlet3(ctx, B, M, side, label, h)
    # 冰白胸甲（只做前半，背后由大衣身片盖住）+ 其上再叠一层隆起的双半月胸甲 + 三道腹甲片
    shell3(ctx, B, f"{T} cuirass", lambda a: B.z(1.668) - 0.040 * s * max(0.0, math.cos(a)) ** 6,
           lambda a: B.z(1.345) - 0.06 * s * max(0.0, math.cos(a)) ** 4, 0.020 * s, M["plate"],
           invdist(["Spine", "Chest"]), trim_mat=M["silver"], trim_r=0.0032 * s, trim_n=32, thick=0.010 * s, nu=36,
           nv=12, a0=-0.98, a1=0.98)
    n1 = len(ctx.parts)
    torso_plates3(ctx, B, M, invdist(["Spine", "Chest"]))
    breast = ctx.parts[n1][0]
    keel = [B.torso_point(0, B.z(z), 0.0465 * s) for z in [1.468 + i * 0.020 for i in range(10)]]
    ctx.part(trim(f"{T} keel", keel, 0.0038 * s, M["silver"], n=3), invdist(["Spine", "Chest"]))
    # 胸甲两侧冷光嵌线：从心晶下方斜向两肋，再折向腰
    for sd in (-1, 1):
        path = [B.torso_point(sd * a, B.z(z), 0.0475 * s) for a, z in
                [(0.16 + 0.35 * i / 8, 1.48 - 0.07 * i / 8) for i in range(9)]]
        ctx.part(trim(f"{T} rib inlay {sd}", path, 0.0020 * s, M["inlay"], n=3), invdist(["Spine", "Chest"]))
    # 大衣身片从背后包到胸前两侧，前襟只露出中间一道冰白胸甲（翻领读作长大衣）
    shell3(ctx, B, f"{T} coat body", lambda a: B.z(1.655) + 0.010 * s * max(0.0, math.cos(a)),
           B.z(1.262), 0.028 * s, M["brocade"], invdist(["Pelvis", "Spine", "Chest"]), trim_mat=M["silver"],
           trim_r=0.0034 * s, trim_n=44, a0=math.pi - 2.30, a1=math.pi + 2.30, nu=48, nv=14, thick=0.007 * s)
    for sd in (-1, 1):
        lap = [B.torso_point(sd * 0.80, B.z(z), 0.038 * s) for z in [1.648 - i * 0.034 for i in range(11)]]
        ctx.part(trim(f"{T} lapel light {sd}", lap, 0.0019 * s, M["inlay"], n=3), invdist(["Pelvis", "Spine", "Chest"]))
    shell3(ctx, B, f"{T} belt", B.z(1.296), B.z(1.246), 0.044 * s, M["steel"], invdist(["Pelvis", "Spine"]),
           trim_mat=M["silver"], trim_r=0.0026 * s, trim_n=44, nu=44, nv=4, thick=0.007 * s)
    # 腰下三片冰白前腹甲叠压，前端收尖
    for k, (zt, zb, g) in enumerate(((1.262, 1.170, 0.058), (1.186, 1.090, 0.054), (1.110, 1.012, 0.050))):
        fp = shell3(ctx, B, f"{T} fauld {k}", B.z(zt), lambda a, zb=zb: B.z(zb) - 0.040 * s * max(0.0, math.cos(a)) ** 3,
                    g * s, M["plate"], rigid("Pelvis"), trim_mat=M["silver"], trim_r=0.0026 * s, trim_n=20,
                    sides=False, a0=-0.74, a1=0.74, nu=20, nv=4, thick=0.0055 * s, top_trim=(k == 0))
        if k == 2:
            icicle_fringe(ctx, fp, M, rigid("Pelvis"), f"{T} fauld icicle", count=7, u0=0.14, u1=0.86, lens=(0.10, 0.045),
                          s=s, seed=2.1)
    buckle = B.on_torso(0, B.z(1.271), 0.054 * s)
    ctx.part(crystal2(f"{T} buckle", buckle - Vector((0, 0, 0.026 * s)), buckle + Vector((0, 0.005 * s, 0.030 * s)),
                      0.019 * s, [M["crystal"]], sides=6, shoulder=0.5, foot=0.1), rigid("Pelvis"))
    gorget2(ctx, B, M["plate"], M["silver"], nu=24)
    build_emblem(ctx, B, M, breast)
    build_collar(ctx, B, M)
    for side, label in SIDES:
        a = B.arms[label]
        spec_p = rigid(("Chest", 0.35), (f"UpperArm.{label}", 0.65))
        lp, shc = pauldron2(ctx, B, side, label, M["plate"], M["silver"], M["glow"], lames=5, radius=0.150,
                            spire=0.095, spire_at=-0.35, spire_dir=(0.35, -0.30, 1.0),
                            theta=((0.04, 0.78), (0.46, 1.02), (0.78, 1.26), (1.06, 1.48), (1.30, 1.68)),
                            shrink=(1.0, 0.972, 0.944, 0.916, 0.888), ridge=0.06, nu=24, nv=7, trim_n=22,
                            trim_r=0.0030)
        # 甲缝冷光嵌线 + 从甲缝里长出的冰晶（越靠上越长，朝外上方）
        for k in range(3):
            line = [lp(k, 2 * i / 16 - 1, 0.50) for i in range(2, 15)]
            line = [p + (p - shc).normalized() * 0.0050 * s for p in line]
            ctx.part(trim(f"{T} pauldron inlay {label}{k}", line, 0.0019 * s, M["inlay"], n=3), spec_p)
        for k in range(4):
            for j, uu in enumerate((-0.66, -0.22, 0.26, 0.62)):
                if k == 3 and j % 2:
                    continue
                b0 = lp(k, uu, 0.95)
                nrm = (b0 - shc).normalized()
                d = (nrm * 0.75 + Vector((0, -0.25, 0.55))).normalized()
                L_ = (0.100 - 0.016 * k) * (1.0 if j not in (1, 2) else 1.30) * s
                ctx.part(crystal2(f"{T} gap crystal {label}{k}{j}", b0 - d * 0.010 * s, b0 + d * L_,
                                  (0.0125 - 0.0020 * k) * s, [M["crystal"]], sides=5, shoulder=0.62, foot=0.6,
                                  seed=k * 3 + j + side), spec_p)
        # 大衣袖：深蓝整圈袖筒包住上臂（袖口霜花），肘口银边；其上叠冰白臂甲、护臂、护肘
        sl = B.s * B.limb
        band(ctx, f"{T} sleeve {label}", a["shoulder"], a["elbow"], 0.056 * sl, 0.051 * sl, M["coat"],
             rigid(f"UpperArm.{label}"), Vector((side, 0, 0.6)), closed=True, v0=0.10, v1=0.94, flare1=0.007 * s,
             thick=0.005 * s, nu=18, nv=6, sub=0, trim_mat=M["silver"], trim_r=0.0026 * s, rims=(1,), rim_n=18)
        arm_armor3(ctx, B, side, label, M, M["crystal"])
        leg_armor3(ctx, B, side, label, M, M["crystal"])
        boot3(ctx, B, M, side, label)
        build_skate(ctx, B, M, side, label)
    hc = build_helm(ctx, B, M)
    build_crystals(ctx, B, M, clear)
    build_blade(ctx, B, M)
    # 冰晶处刑大剑：斜背在背后，柄头从右肩后探出、刃尖指向左后腰
    d = Vector((0.37, 0.08, 0.925)).normalized()
    guard = Vector((0.070 * s, -0.240 * s, B.z(1.700)))
    tip, pommel = executioner_sword(ctx, M, guard, d, (0, -1, 0), rigid("Chest"), clear, blade_len=0.80, s=s,
                                    width=0.064)
    clear.capsule("Chest", guard - d * 0.04 * s, tip + d * 0.04 * s, 0.034 * s, "sword blade")
    for k, t in enumerate((0.18, 0.52)):
        p = guard - d * 0.80 * s * t
        back = B.on_torso(p.x, p.z, 0.034 * s, back=True)
        ctx.part(tube(f"{T} sword clamp {k}", [back, p + Vector((0, 0.012 * s, 0))], [0.009 * s, 0.008 * s],
                      [M["steel"]], n=6, per=1), rigid("Chest"))
    coat = coat_wrap(B)
    coat.build(ctx, [M["coat"], M["lining"]], f"{T} coat skirt", nu=90, nv=30, uv_scale=2.0)
    cloth_edges(ctx, coat, f"{T} coat skirt", 0.0036 * s, M["silver"], count=30)
    hem_line(ctx, coat, f"{T} coat skirt hem", 0.0030 * s, M["hem"], count=170, n=3)
    # 燕尾尖端各垂一枚冰晶坠
    for k, a in enumerate((math.pi - 0.44, math.pi + 0.44)):
        u = (a - coat.a0) / (coat.a1 - coat.a0)
        p = radial(coat.point(u, 1.0), 0.002 * s)
        ctx.part(crystal2(f"{T} tail pendant {k}", p + Vector((0, 0, 0.010 * s)), p - Vector((0, 0, 0.070 * s)),
                          0.012 * s, [M["crystal"]], sides=6, shoulder=0.45, foot=0.6, seed=k * 2.1),
                 ("garment", coat))
    # 自检胶囊体
    for side, label in SIDES:
        a = B.arms[label]
        clear.capsule(f"UpperArm.{label}", a["shoulder"], a["elbow"], 0.072 * s, f"upper arm {label}")
        clear.capsule(f"Forearm.{label}", a["elbow"], a["wrist"], 0.062 * s, f"forearm {label}")
        h = B.hands[label]
        clear.capsule(f"Hand.{label}", h["wrist"], h["knuckle"], 0.056 * s, f"hand {label}")
    clear.capsule("Head", hc - Vector((0, 0, 0.07 * s)), hc + Vector((0, 0, 0.06 * s)), 0.118 * s, "helm")
    tally(ctx)
    return {"B": B, "coat": coat, "clear": clear, "hc": hc, "coat_rep": []}


class Clearance2(Clearance):
    """动作穿插自检：同一件刚性物（大剑）上的采样点不与自身胶囊体比较。"""

    def gap(self, rig, pose):
        cache = {}
        caps = [(self.world(rig, pose, b, a, cache), self.world(rig, pose, b, c, cache), r, tag)
                for b, a, c, r, tag in self.caps]
        best = (1e9, "", "")
        for bone, p, tag in self.points:
            w = self.world(rig, pose, bone, p, cache)
            for a, c, r, ctag in caps:
                if tag.split()[0] == ctag.split()[0]:
                    continue
                ab = c - a
                t = clamp((w - a).dot(ab) / max(ab.length_squared, 1e-12))
                g = (w - a.lerp(c, t)).length - r
                if g < best[0]:
                    best = (g, tag, ctag)
        return best


def tally(ctx):
    """按首材质统计三角面（发光 / 滚边 / 冰晶不参与游戏版减面，要从源头控制）。
    同时给没有 UV 的部件补一层全零 UVMap：kit 按材质合并时若首个部件没有 UV，合并后的网格没有激活 UV，
    贴图会整体失效（上一轮漆甲雕花“看不见”的根因）。全零 UV 采样贴图左下角，即冰白外框色。"""
    out = {}
    for obj, _ in ctx.parts:
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap", do_init=False)
    for obj, _ in ctx.parts:
        m = obj.data.materials[0].name if obj.data.materials else "?"
        out[m] = out.get(m, 0) + sum(len(p.vertices) - 2 for p in obj.data.polygons)
    keep = sum(v for k, v in out.items() if any(w in k.lower() for w in LOD_KEEP))
    if os.environ.get("ISOLDE_PARTS"):
        # 调试：按“名字去掉序号与左右”分组统计三角面，找出面数大户
        import re
        groups = {}
        for obj, _ in ctx.parts:
            key = re.sub(r"[0-9.\-]+|\b[LR]\b", "", obj.name).strip()
            groups[key] = groups.get(key, 0) + sum(len(p.vertices) - 2 for p in obj.data.polygons)
        for k, v in sorted(groups.items(), key=lambda kv: -kv[1])[:40]:
            print(f"ISOLDE PART {v:6d} {k}")
    print("ISOLDE TRIS", {k: v for k, v in sorted(out.items(), key=lambda kv: -kv[1])}, "total", sum(out.values()),
          "lod-keep", keep)


def skeleton(rig, st):
    B = st["B"]
    s = B.s
    add_skeleton(rig, B)
    for side, label in SIDES:
        sh = B.arms[label]["shoulder"]
        rig.bone(f"Frost.{label}", sh, sh + Vector((0, 0, 0.12 * s)), "Chest", roll=Y)
    back = B.torso_point(math.pi, B.z(1.480), 0.034 * s)
    rig.bone("FrostBack", back, back + Vector((0, -0.06 * s, 0.10 * s)), "Chest", roll=Z)
    rig.translate["FrostBack"] = "_frost"
    rig.add_garment(st["coat"])


# ===== 动作 =====
def frost(pose, flare=0.0, breathe=0.0, follow=0.40):
    """冰晶簇：肩簇跟随上臂转动的一部分（与肩甲的混合权重一致），flare 为外张，breathe 为呼吸起伏。"""
    # 绕 +X 正转让朝上的晶簇向身后（-Y）倒；绕 Y 按左右号外倒
    for label, sd in (("L", -1), ("R", 1)):
        arm = pose.get(f"UpperArm.{label}", I3)
        pose[f"Frost.{label}"] = R((Y, sd * (flare * 0.9 + breathe)), (X, flare * 0.5)) @ mat_slerp(arm, follow)
    pose["FrostBack"] = R((X, flare * 0.55 + breathe * 0.5))
    pose["_frost"] = Vector((0, -0.02 * flare, 0.04 * flare))


def coat(rig, st, pose, back, flare, spread=0.0):
    """长大衣：统一随风后扬 + 少量外鼓，两条燕尾可左右分开；再逐链检查，腿穿出布面的链继续外掀让位。"""
    g = st["coat"]
    mid = (g.K - 1) / 2

    def side(k, j):
        return spread * (1 if k < mid else -1) * (1.0 if abs(k - mid) < 1.0 else 0.4)
    coat_clear(rig, g, pose, st["B"], back, flare, side if spread else None, report=st["coat_rep"])


def idle_pose(rig, st, t):
    B = st["B"]
    s = B.s
    p = idle(rig, B, t, breathe=0.02, sway=0.010, arms=0.03)
    legs = Legs(rig, B)
    # 冰面上的丁字站姿：左脚前外撇、右脚在后；随冰面极缓地漂移
    p["_hover"] = Vector((0.010 * s * math.sin(t), 0.0, -0.016 * s + 0.004 * s * math.sin(2 * t)))
    p["Pelvis"] = R((Z, 0.06 + 0.02 * math.sin(t)), (Y, 0.012 * math.sin(t)))
    p["Head"] = R((X, -0.06 + 0.015 * math.sin(t + 2.2)), (Z, -0.05 + 0.03 * math.sin(t)))
    for label, off, yaw in (("L", (0.012, 0.060), 0.32), ("R", (-0.008, -0.050), -0.46)):
        a = legs.rest[label]["ankle"] + Vector((off[0] * s, off[1] * s, 0))
        legs.plant(p, label, a, yaw=yaw, knee_out=0.2)
    # 右手自然垂在身侧、左手微收于腹前——冷静的执行官
    for label, sg in (("L", -1), ("R", 1)):
        p[f"UpperArm.{label}"] = R((Y, sg * (0.20 + 0.03 * math.sin(t + 0.5 * sg))), (X, 0.05 + 0.02 * math.sin(t + 1)))
        p[f"Forearm.{label}"] = R((X, (0.20 if sg > 0 else 0.42) + 0.03 * math.sin(t + 1.4)))
        fingers(p, B, label, lambda i: 0.25 + 0.05 * math.sin(2 * t + i * 0.6))
    frost(p, breathe=0.03 * math.sin(2 * t))
    coat(rig, st, p, lambda k, j: 0.03 + 0.02 * math.sin(t + k * 0.8 + j * 0.9),
         lambda k, j: 0.02 + 0.015 * math.sin(t + k + j * 0.7))
    return p


def move_pose(rig, st, t):
    B = st["B"]
    p = skate3(rig, B, t)
    for label in ("L", "R"):
        fingers(p, B, label, lambda i: 0.10 + 0.06 * i)
    frost(p, breathe=0.02 * math.sin(2 * t))
    coat(rig, st, p, lambda k, j: 0.15 + 0.04 * math.sin(2 * t + k * 0.8 + j),
         lambda k, j: 0.04 + 0.02 * math.sin(2 * t + k * 0.7 + j * 1.1), spread=0.06)
    return p


def stance(rig, B, pose, lf, rf, sink, yaw_l=0.0, yaw_r=0.0, shift=(0.0, 0.0)):
    """冰面架势：lf、rf 为左右脚踝相对静止位置的偏移 (x, y)，shift 为重心水平偏移。"""
    legs = Legs(rig, B)
    pose["_hover"] = Vector((shift[0] * B.s, shift[1] * B.s, -sink * B.s))
    for label, off, yaw in (("L", lf, yaw_l), ("R", rf, yaw_r)):
        a = legs.rest[label]["ankle"] + Vector((off[0] * B.s, off[1] * B.s, 0))
        legs.plant(pose, label, a, yaw=yaw, knee_out=0.22)


def cast_key(rig, st, stage):
    """寒霜领域：0 起势、1 蓄力（上身左拧、右掌收到左肩前凝寒）、2 横扫（右臂伸直自左向右掠过、掌心压向前方扇区）、
    3 收势（手臂扫到右后方定格）。"""
    B = st["B"]
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    hR, hL = B.hands["R"], B.hands["L"]
    if stage == 1:
        p["Pelvis"] = R((Z, 0.26), (X, -0.06))
        p["Spine"] = R((Z, 0.18))
        p["Chest"] = R((Z, 0.28), (X, 0.04))
        p["Head"] = R((Z, -0.36), (X, -0.06))
        stance(rig, B, p, (0.00, 0.20), (0.06, -0.20), 0.110, 0.35, -0.55, (-0.02, 0.0))
        rig.aim(p, "UpperArm.R", (-0.42, 0.62, 0.12))
        rig.aim(p, "Forearm.R", (-0.88, 0.12, 0.40))
        rig.aim(p, "Hand.R", (-0.60, -0.10, 0.78), up=(-0.2, 0.9, -0.2), rest_up=hR["n"])
        rig.aim(p, "UpperArm.L", (-0.64, -0.32, -0.70))
        rig.aim(p, "Forearm.L", (-0.56, -0.44, -0.70))
        rig.aim(p, "Hand.L", (-0.50, -0.50, -0.70), up=(0, -0.3, -1), rest_up=hL["n"])
        fingers(p, B, "R", 0.55)
        fingers(p, B, "L", -0.05, 0.8)
        frost(p, flare=0.14)
        coat(rig, st, p, lambda k, j: 0.07, lambda k, j: 0.06)
    else:
        follow = stage == 3
        p["Pelvis"] = R((Z, -0.26 if not follow else -0.32), (X, -0.16))
        p["Spine"] = R((Z, -0.18), (X, -0.05))
        p["Chest"] = R((Z, -0.28 if not follow else -0.36))
        p["Head"] = R((Z, 0.30 if not follow else 0.36), (X, 0.02))
        stance(rig, B, p, (0.02, 0.28), (0.08, -0.22), 0.135, 0.25, -0.60, (0.03, 0.05))
        d = (0.72, 0.68, 0.10) if not follow else (0.97, 0.16, 0.04)
        rig.aim(p, "UpperArm.R", d)
        rig.aim(p, "Forearm.R", (d[0] * 1.02, d[1] * 0.96, d[2] - 0.02))
        rig.aim(p, "Hand.R", (d[0], d[1] * 0.92, d[2] - 0.22), up=(0.25, 0.35, -0.90), rest_up=hR["n"])
        rig.aim(p, "UpperArm.L", (-0.80, -0.42, -0.30))
        rig.aim(p, "Forearm.L", (-0.78, -0.50, -0.20))
        rig.aim(p, "Hand.L", (-0.72, -0.55, -0.12), up=(0.2, 0.2, -1.0), rest_up=hL["n"])
        fingers(p, B, "R", -0.12, 1.0)
        fingers(p, B, "L", 0.85)
        frost(p, flare=0.26 if not follow else 0.18)
        coat(rig, st, p, lambda k, j: 0.13, lambda k, j: 0.10)
    return p


def channel_key(rig, st, stage):
    """绝对零度：右臂笔直擎天，左掌向前下方压住冰面，胸腔后仰、仰头，冰晶全面外张、大衣被寒潮掀起。"""
    B = st["B"]
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    hR, hL = B.hands["R"], B.hands["L"]
    p["Pelvis"] = R((X, 0.02))
    p["Spine"] = R((X, 0.05))
    p["Chest"] = R((X, 0.09), (Z, 0.05))
    p["Neck"] = R((X, 0.06))
    p["Head"] = R((X, 0.14), (Z, 0.06))
    stance(rig, B, p, (-0.12, 0.08), (0.12, -0.06), 0.130, 0.42, -0.45)
    rig.aim(p, "UpperArm.R", (0.24, 0.12, 0.96))
    rig.aim(p, "Forearm.R", (0.12, 0.10, 0.99))
    rig.aim(p, "Hand.R", (0.06, 0.08, 1.0), up=(-0.3, 1.0, 0.0), rest_up=hR["n"])
    # 左臂向左前下方伸直、掌心朝地压下
    rig.aim(p, "UpperArm.L", (-0.78, 0.30, -0.55))
    rig.aim(p, "Forearm.L", (-0.76, 0.34, -0.55))
    rig.aim(p, "Hand.L", (-0.70, 0.36, -0.60), up=(-0.2, 0.2, -1), rest_up=hL["n"])
    fingers(p, B, "R", -0.12, 1.0)
    fingers(p, B, "L", -0.10, 1.0)
    frost(p, flare=0.40, follow=0.30)
    coat(rig, st, p, lambda k, j: 0.08, lambda k, j: 0.11)
    return p


def animate(rig, st):
    clear = st["clear"]
    rep = st["coat_rep"]

    def coat_report(clip):
        print(f"COAT CLEARANCE {clip}: worst leg poke-through {max(rep) * 100:.1f} cm over {len(rep)} poses")
        rep.clear()
    rig.loop("Idle", 72, lambda t: idle_pose(rig, st, t))
    coat_report("Idle")
    rig.loop("Move", 32, lambda t: move_pose(rig, st, t), step=1)
    coat_report("Move")
    k = [cast_key(rig, st, i) for i in range(4)]
    cast = [(1, k[0]), (8, k[1]), (14, k[2]), (20, k[3]), (32, k[0])]
    rig.keyed("Cast", cast)
    coat_report("Cast")
    c = [channel_key(rig, st, i) for i in range(2)]
    channel = [(1, c[0]), (13, c[1]), (28, c[1]), (42, c[0])]
    rig.keyed("Channel", channel)
    coat_report("Channel")
    clear.report(rig, "Idle", [idle_pose(rig, st, TAU * i / 24) for i in range(24)])
    clear.report(rig, "Move", [move_pose(rig, st, TAU * i / 32) for i in range(32)])
    clear.report(rig, "Cast", keyed_samples(cast))
    clear.report(rig, "Channel", keyed_samples(channel))
    rep.clear()
