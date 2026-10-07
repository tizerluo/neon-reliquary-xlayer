"""Boss 0 · 余烬之王 · 熔炉君主（The Cinder King · Furnace Sovereign）。

设定：约 6 m 的熔岩巨人王。黑曜 / 铸铁躯体布满发光熔岩裂纹；熔金王冠上悬一圈旋转的余烬光环；
双肩后方升起哥特王座式“炉墙”——玫瑰窗熔炉作为头后光环，两侧烟囱塔喷吐火舌；背后是缝着锁链与
余烬提灯的符文披风；一双巨拳的指节发光。
动作：Idle（沉重呼吸）/ Move（重步踏地）/ Attack（高举双拳砸地）/ Enrage（仰天咆哮，王冠与炉墙爆燃）。
"""

import math

from mathutils import Matrix, Vector

from kit.core import (TAU, auto_smooth, chain, crack_maps, filigree_maps, finish, garment, gem, invdist, join,
                      lathe, lerp, orient, plate, rigid, rune_maps, smoothstep, spike, surface, trim, tube)
from kit.garment import Panel, Wrap
from kit.humanoid import SIDES, Body, cuisse, greave, limb_plate, pauldron, rerebrace, shell, vambrace
from kit.motion import Legs, gait
from kit.rig import R, X, Y, Z

from chars import _b0fx_flame as FX
from chars._bossA_common import (blob, bbox_report, chain_links, ground_check, loop, magma_maps, sampled,
                                 seam_check, shards, studs, sweep, track, with_defaults)

TITLE = "Cinder King"
ACCENT = (1.0, 0.52, 0.42)
CLIPS = ("Idle", "Move", "Attack", "Enrage")
GAME_TRIS = 85000
LOD_KEEP = ("inlay", "glow", "hem", "core", "flame")
REVIEW_POSE = ("Idle", 1)
EMBER = (1.0, 0.42, 0.12)
GOLD_HOT = (1.0, 0.62, 0.22)
FIST = 0.46            # 拳头半径（米）


# ===== 材质 =====
def materials(ctx):
    M = ctx.M
    ctx.mat("body", "obsidian magma skin", (0.02, 0.018, 0.02), metal=0.3, rough=0.30, coat=0.35)
    ctx.texture("body", magma_maps(EMBER, base_rgb=(0.020, 0.017, 0.021), size=1024, seed=7, cells=5, width=0.055,
                                   fine=0.20, heat=1.0, hot=0.3), emit_strength=3.0, normal_strength=0.9)
    ctx.mat("iron", "blackened iron plate", (0.075, 0.068, 0.066), metal=0.92, rough=0.32, coat=0.2)
    ctx.texture("iron", filigree_maps((0.085, 0.076, 0.072), (0.32, 0.20, 0.08), size=1024, seed=12, density=14,
                                      width=2), normal_strength=0.5)
    ctx.mat("gold", "molten gold", (1.0, 0.64, 0.26), metal=1.0, rough=0.24, emit=(1.0, 0.40, 0.08), strength=0.25)
    ctx.mat("trim", "molten gold trim", (1.0, 0.66, 0.28), metal=1.0, rough=0.22, emit=(1.0, 0.40, 0.08),
            strength=0.3)
    ctx.mat("brick", "furnace brick", (0.05, 0.035, 0.03), metal=0.4, rough=0.45)
    ctx.texture("brick", magma_maps(EMBER, base_rgb=(0.040, 0.030, 0.028), size=1024, seed=21, cells=7, width=0.04,
                                    fine=0.15, heat=0.8, hot=0.2), emit_strength=2.4, normal_strength=0.8)
    ctx.mat("cape", "charred rune banner", (0.05, 0.018, 0.012), rough=0.82, sheen=0.1, sheen_tint=(1, 0.5, 0.3),
            spec=0.3)
    ctx.texture("cape", rune_maps(EMBER, base_rgb=(0.050, 0.016, 0.010), line_rgb=(0.20, 0.06, 0.02), size=1024,
                                  seed=31, rows=7, cols=9), emit_strength=2.6)
    ctx.mat("lining", "ember satin lining", (0.16, 0.035, 0.015), rough=0.5, sheen=0.3, sheen_tint=(1, 0.6, 0.4))
    ctx.mat("glow", "ember core glow", (1.0, 0.55, 0.25), emit=(1.0, 0.50, 0.16), strength=6.0)
    ctx.mat("magma", "magma glass glow", (0.8, 0.18, 0.03), emit=(1.0, 0.30, 0.05), strength=3.5)
    ctx.texture("magma", magma_maps((1.0, 0.78, 0.35), base_rgb=(0.55, 0.10, 0.02), size=512, seed=3, cells=4,
                                    width=0.07, fine=0.3, heat=1.0, hot=0.6), emit_strength=5.0, normal_strength=0.3)
    ctx.mat("hem", "ember hem light", (1.0, 0.5, 0.2), emit=EMBER, strength=4.0)
    # 火焰：半透明图集材质（外层橙红 / 内层黄白 / 火星），强度 <= 2.5；喷口环为细管烧红自发光
    M["flame"] = FX.flame_material(f"{ctx.title} furnace flame", 2.3)
    FX.ring_material(ctx, "furnace vent ring glow", 1.6)
    ctx.mat("chain", "black iron chain", (0.09, 0.08, 0.075), metal=1.0, rough=0.3)
    return M


# ===== 巨人比例 =====
def giant_body():
    """在 kit Body 上覆盖比例：短粗腿、巨胸、头低陷在两肩之间、长臂巨拳。"""
    B = Body(height=5.0, shoulder=0.5)
    B.hip_z, B.knee_z, B.ankle_z = 2.05, 1.12, 0.32
    B.pelvis_z, B.waist_z, B.chest_z = 2.30, 2.75, 3.45
    B.shoulder_z, B.neck_base, B.chin, B.head_top = 4.00, 4.18, 4.34, 5.10
    B.head_c = Vector((0, 0.42, 4.68))
    B.torso = [(1.92, (0.66, 0.52, -0.02)), (2.20, (0.86, 0.62, -0.02)), (2.50, (0.82, 0.60, 0.00)),
               (2.75, (0.76, 0.60, 0.04)), (3.05, (0.88, 0.70, 0.08)), (3.40, (1.02, 0.80, 0.10)),
               (3.72, (1.10, 0.82, 0.08)), (3.98, (1.00, 0.72, 0.02)), (4.12, (0.72, 0.60, 0.06)),
               (4.26, (0.44, 0.44, 0.14))]
    B.arms, B.hands, B.legs = {}, {}, {}
    for side, label in SIDES:
        S = Vector((side * 1.24, -0.02, 3.96))
        E = Vector((side * 1.74, 0.02, 2.80))
        W = Vector((side * 1.92, 0.34, 1.74))
        B.arms[label] = {"shoulder": S, "elbow": E, "wrist": W, "inner": Vector((side * 0.7, 0, 3.95))}
        B.legs[label] = {"hip": Vector((side * 0.56, -0.02, 2.05)), "knee": Vector((side * 0.64, 0.14, 1.12)),
                         "ankle": Vector((side * 0.68, -0.06, 0.34)), "ball": Vector((side * 0.72, 0.56, 0.10)),
                         "toe": Vector((side * 0.74, 0.92, 0.07))}
    return B


def fist_frame(B, label):
    a = B.arms[label]
    f = (a["wrist"] - a["elbow"]).normalized()
    k = Vector((0, 1, -0.2))
    k = (k - f * k.dot(f)).normalized()
    sv = f.cross(k).normalized()
    return f, k, sv


# ===== 躯干 =====
def torso_shape(B, a, z):
    """肌肉起伏：胸大肌、斜方肌、脊沟、腹块。"""
    front = max(0.0, math.cos(a))
    back = max(0.0, -math.cos(a))
    x = math.sin(a)
    pec = 0.09 * math.exp(-((z - 3.55) / 0.22) ** 2) * front ** 1.5 * (1 - 0.7 * math.exp(-(x / 0.12) ** 2))
    trap = 0.10 * math.exp(-((z - 4.02) / 0.12) ** 2) * math.exp(-((abs(x) - 0.62) / 0.22) ** 2)
    groove = -0.05 * math.exp(-(x / 0.10) ** 2) * back * smoothstep(2.4, 2.9, z)
    abs_ = 0.035 * front ** 2 * math.exp(-((z - 2.95) / 0.28) ** 2) * (0.5 + 0.5 * math.cos(z * 22)) * \
        (1 - math.exp(-(x / 0.05) ** 2))
    return pec + trap + groove + abs_


def build_torso(ctx, B, M):
    z0, z1 = B.torso[-1][0], B.torso[0][0]

    def pt(u, v):
        a = u * TAU
        z = lerp(z0, z1, v)
        return B.torso_point(a, z, torso_shape(B, a, z))
    body = surface(f"{ctx.title} torso", pt, 56, 34, [M["body"]], closed_u=True,
                   uvfn=lambda u, v: (u * 2, (1 - v) * 0.8))
    orient(body, lambda c: Vector((0, 0.05, c.z)))
    ctx.part(finish(body, None, 1, 1), invdist(["Pelvis", "Spine", "Chest", "Neck"], 0.25))
    ctx.part(blob(f"{ctx.title} crotch", (0, -0.02, 2.02), (0.62, 0.48, 0.22), [M["body"]], 24, 12),
             rigid("Pelvis"))
    neck = sweep(f"{ctx.title} neck", [(0, 0.06, 3.98), (0, 0.18, 4.22), (0, 0.32, 4.44)], [0.46, 0.40, 0.34],
                 [M["body"]], n=20, per=3, tile=2.4)
    ctx.part(neck, invdist(["Chest", "Neck", "Head"], 0.12))


# ===== 头与王冠 =====
CROWN_C = Vector((0, 0.42, 4.90))
HALO_C = Vector((0, 0.32, 6.12))
HALO_R = 0.70


HEAD_R = (0.38, 0.42, 0.42)
CROWN_R = (0.39, 0.43)


def build_head(ctx, B, M):
    hc = B.head_c
    head = blob(f"{ctx.title} helm", hc, HEAD_R, [M["iron"]], 36, 22, power=2.3,
                shape=lambda p: 0.05 * math.exp(-((p.z + 0.02) / 0.05) ** 2) * max(0.0, p.y / 0.42) ** 2)
    ctx.part(head, rigid("Head"))
    # 熔金死亡面具：眉弓、颧骨、鼻梁，眼窝与口中透出炉火
    mask_c = hc + Vector((0, 0.36, -0.02))
    W, T, Bt = 0.68, 0.24, 0.56

    def mp(u, v):
        x = (u - 0.5) * W
        z = T - v * Bt
        y = 0.08 - 1.25 * x * x - 0.6 * max(0.0, z - 0.12) ** 2
        y += 0.045 * math.exp(-((z - 0.085) / 0.035) ** 2) * (1 - 0.5 * math.exp(-(x / 0.03) ** 2))   # 眉弓
        y += 0.035 * math.exp(-((abs(x) - 0.16) / 0.06) ** 2 - ((z + 0.035) / 0.05) ** 2)            # 颧骨
        y += 0.06 * math.exp(-(x / 0.04) ** 2) * smoothstep(0.09, -0.07, z) * smoothstep(-0.14, -0.06, z)   # 鼻梁
        y -= 0.04 * math.exp(-((abs(x) - 0.105) / 0.055) ** 2 - ((z - 0.035) / 0.035) ** 2)          # 眼窝
        return mask_c + Vector((x, y, z))

    def on_mask(x, z, lift=0.0):
        return mp(0.5 + x / W, (T - z) / Bt) + Vector((0, lift, 0))
    mask = surface(f"{ctx.title} mask", mp, 34, 26, [M["gold"]])
    orient(mask, lambda c: hc)
    ctx.part(finish(mask, 0.03, -1, 1), rigid("Head"))
    for sd in (-1, 1):
        # 眼窝深处的熔火 + 斜挑的发光眼缝
        ctx.part(blob(f"{ctx.title} eye socket {sd}", on_mask(sd * 0.105, 0.035, -0.012), (0.075, 0.03, 0.036),
                      [M["magma"]], 16, 8), rigid("Head"))
        eye = [on_mask(sd * (0.045 + 0.13 * t), 0.022 + 0.045 * t ** 1.3, 0.004) for t in [i / 8 for i in range(9)]]
        ctx.part(tube(f"{ctx.title} eye {sd}", eye, [0.020, 0.026, 0.028, 0.028, 0.026, 0.023, 0.019, 0.014, 0.008],
                      [M["glow"]], n=8, fy=0.55, up=(0, 0, 1)), rigid("Head"))
    # 口栅：熔火从金栅间透出
    ctx.part(blob(f"{ctx.title} maw", on_mask(0, -0.19, -0.03), (0.17, 0.06, 0.075), [M["magma"]], 18, 10),
             rigid("Head"))
    for k in range(7):
        x = (k - 3) * 0.045
        ctx.part(tube(f"{ctx.title} maw bar {k}", [on_mask(x, -0.13, 0.012), on_mask(x, -0.26, 0.012)],
                      [0.013, 0.013], [M["trim"]], n=6, per=1), rigid("Head"))
    lip = [on_mask(x, -0.12 - 0.02 * (x / 0.17) ** 2, 0.014) for x in [(i / 16 - 0.5) * 0.36 for i in range(17)]]
    ctx.part(trim(f"{ctx.title} maw lip", lip, 0.014, M["trim"]), rigid("Head"))
    # 熔金胡须：下颌垂下的尖刺
    for k in range(11):
        x = (k - 5) * 0.052
        base = on_mask(x, -0.30, -0.01)
        L = 0.42 - abs(k - 5) * 0.045
        ctx.part(spike(f"{ctx.title} beard {k}", base, base + Vector((x * 0.35, 0.08, -L)), 0.038, [M["gold"]],
                       sides=5, bend=0.03, up=(0, 1, 0)), rigid("Head"))
    ctx.part(gem(f"{ctx.title} brow gem", on_mask(0, 0.11, 0.02), 0.045, M["glow"], (0.7, 0.5, 1.3)), rigid("Head"))
    # 两鬓的熔金角饰
    for side, label in SIDES:
        base = hc + Vector((side * 0.34, 0.06, 0.10))
        ctx.part(spike(f"{ctx.title} temple horn {label}", base, base + Vector((side * 0.46, -0.10, 0.36)), 0.10,
                       [M["gold"]], sides=7, bend=0.10, up=(side, 0, 1)), rigid("Head"))
    build_crown(ctx, M)


def crown_point(a, r_scale=1.0, z=0.0):
    return Vector((math.sin(a) * CROWN_R[0] * r_scale, CROWN_C.y + math.cos(a) * CROWN_R[1] * r_scale, CROWN_C.z + z))


def build_crown(ctx, M):
    c = CROWN_C
    band = lathe(f"{ctx.title} crown band", [(1.0, c.z + 0.16), (1.02, c.z + 0.07), (1.04, c.z - 0.05),
                                             (1.0, c.z - 0.09)], [M["gold"]], segments=48, center=(0, c.y, 0),
                 sx=CROWN_R[0], sy=CROWN_R[1])
    ctx.part(finish(band, 0.03, 1, 0), rigid("Head"))
    for zz, rs in ((0.15, 1.09), (-0.08, 1.11)):
        ring = [crown_point(t, rs, zz) for t in [i / 64 * TAU for i in range(64)]]
        ctx.part(trim(f"{ctx.title} crown rim {zz:.2f}", ring, 0.016, M["trim"], closed=True), rigid("Head"))
    for k, (tip, L, tall) in enumerate(build_crown_tips()):
        a = k / 8 * TAU
        base = crown_point(a, 1.0, 0.08)
        ctx.part(spike(f"{ctx.title} crown spire {k}", base, tip, 0.09 if tall else 0.065, [M["gold"]], sides=6),
                 rigid("Head"))
        mid = base.lerp(tip, 0.28) + Vector((math.sin(a), math.cos(a), 0)) * 0.05
        ctx.part(gem(f"{ctx.title} crown gem {k}", mid, 0.048 if tall else 0.034, M["glow"], (0.8, 0.6, 1.4)),
                 rigid("Head"))


def build_crown_flames(ctx, M, tips):
    """王冠尖顶的火舌：分层半透明（外层橙红 + 内层黄白细芯），每根 Flare 骨一个网格、一个图集材质。"""
    for k, (tip, L, tall) in enumerate(tips):
        big = k == 0
        f = FX.flame_bundle(f"{ctx.title} crown flame {k}", tip - Vector((0, 0, 0.08)), (0, 0, 1),
                            0.58 if big else (0.46 if tall else 0.31), 0.098 if tall else 0.072, M["flame"],
                            seed=k * 1.3 + 0.4, n_out=3 if tall else 2, n_in=2 if tall else 1, sparks=0)
        ctx.attach(f, f"Flare{k}")


def build_halo(ctx, M):
    """悬浮余烬光环：12 枚熔金尖晶 + 细环，挂 Halo 骨在动作里旋转。"""
    c = HALO_C
    objs = [tube(f"{ctx.title} halo ring", [c + Vector((math.sin(t) * HALO_R, math.cos(t) * HALO_R, 0))
                                            for t in [i / 72 * TAU for i in range(72)]],
                 [0.016] * 72, [M["trim"]], n=6, closed=True, per=1)]
    items = []
    for k in range(12):
        a = k / 12 * TAU
        r0 = HALO_R
        base = c + Vector((math.sin(a) * r0, math.cos(a) * r0, 0))
        L = 0.30 if k % 3 == 0 else 0.18
        items.append((base - Vector((0, 0, 0.05)), base + Vector((math.sin(a) * 0.05, math.cos(a) * 0.05, L)), 0.05))
    objs.append(shards(f"{ctx.title} halo shards", items, [M["gold"]], sides=4))
    for k in range(4):
        a = (k + 0.5) / 4 * TAU
        objs.append(gem(f"{ctx.title} halo ember {k}", c + Vector((math.sin(a) * HALO_R, math.cos(a) * HALO_R, 0)), 0.06,
                        M["glow"], (1, 1, 1)))
    halo = join(objs, f"{ctx.ID}_HALO", c)
    ctx.attach(halo, "Halo", keep=True)


# ===== 手臂与巨拳 =====
def build_arms(ctx, B, M):
    s = B.s
    for side, label in SIDES:
        a = B.arms[label]
        S, E, W = a["shoulder"], a["elbow"], a["wrist"]
        arm = sweep(f"{ctx.title} arm {label}", [a["inner"], S, S.lerp(E, 0.5), E, E.lerp(W, 0.5), W],
                    [0.50, 0.46, 0.42, 0.36, 0.33, 0.30], [M["body"]], n=22, per=3, tile=3.2)
        ctx.part(arm, chain([f"UpperArm.{label}", f"Forearm.{label}", f"Hand.{label}"], "Chest", 0.18))
        ctx.part(blob(f"{ctx.title} deltoid {label}", S + Vector((side * 0.08, 0, -0.10)), (0.50, 0.48, 0.55),
                      [M["body"]], 24, 14, tile=3.2), rigid(("Chest", 0.3), (f"UpperArm.{label}", 0.7)))
        pauldron(ctx, B, side, label, M["iron"], M["trim"], M["glow"], lames=4, radius=0.27, spread=1.36, rise=1.2,
                 tilt=0.34, spire=0.20, spire_at=-0.15, spire_dir=(0.35, -0.15, 1.0),
                 theta=((0.05, 0.88), (0.60, 1.22), (1.00, 1.52), (1.34, 1.80)), shrink=(1.0, 0.95, 0.90, 0.86),
                 thick=0.035, trim_r=0.0055, ridge=0.05)
        # 肩甲外侧三根熔金犄角
        sh = S + Vector((0, 0, 0.05 * s))
        for k, (ang, L) in enumerate(((0.35, 0.72), (0.0, 0.95), (-0.35, 0.62))):
            d = Vector((side * 0.55, math.sin(ang) * 0.9 - 0.15, 1.0)).normalized()
            base = sh + Vector((side * 0.30, math.sin(ang) * 0.35, 0.40))
            ctx.part(spike(f"{ctx.title} pauldron horn {label}{k}", base, base + d * L, 0.10, [M["gold"]], sides=7,
                           bend=0.10, up=(side, 0, 0)), rigid(("Chest", 0.35), (f"UpperArm.{label}", 0.65)))
        rerebrace(ctx, B, side, label, M["iron"], M["trim"], r=(0.19, 0.165), thick=0.03, trim_r=0.012)
        vambrace(ctx, B, side, label, M["iron"], M["trim"], inlay=M["glow"], r=(0.150, 0.158),
                 spur=(M["gold"], 0.16), thick=0.03, trim_r=0.012)
        ctx.part(blob(f"{ctx.title} couter {label}", E + Vector((side * 0.10, -0.22, 0.02)), (0.24, 0.22, 0.26),
                      [M["iron"]], 20, 12, power=2.4),
                 rigid((f"UpperArm.{label}", 0.5), (f"Forearm.{label}", 0.5)))
        build_fist(ctx, B, M, side, label)


def build_fist(ctx, B, M, side, label):
    a = B.arms[label]
    W = a["wrist"]
    f, k, sv = fist_frame(B, label)
    C = W + f * 0.40
    frame = Matrix((sv, k, f)).transposed()
    spec = rigid(f"Hand.{label}")
    ctx.part(blob(f"{ctx.title} fist {label}", C, (0.40, 0.40, 0.44), [M["body"]], 28, 18, power=2.7, frame=frame,
                  tile=2.0), spec)
    xs = (-0.27, -0.09, 0.09, 0.27)
    for i, x in enumerate(xs):
        o = sv * x
        path = [C + o + k * 0.22 - f * 0.02, C + o + k * 0.40 + f * 0.20, C + o + k * 0.36 + f * 0.42,
                C + o + k * 0.12 + f * 0.50]
        ctx.part(sweep(f"{ctx.title} finger {label}{i}", path, [0.11, 0.115, 0.105, 0.09], [M["body"]], n=12, per=3,
                       tile=2.0), spec)
        knuck = C + o + k * 0.47 + f * 0.24
        ctx.part(blob(f"{ctx.title} knuckle plate {label}{i}", knuck, (0.10, 0.06, 0.11), [M["iron"]], 14, 8,
                      power=2.5, frame=frame), spec)
        ctx.part(spike(f"{ctx.title} knuckle spike {label}{i}", knuck + k * 0.04, knuck + k * 0.20 + f * 0.04, 0.045,
                       [M["gold"]], sides=5), spec)
        ctx.part(gem(f"{ctx.title} knuckle ember {label}{i}", knuck + k * 0.035 - f * 0.08, 0.035, M["glow"],
                     (1.0, 1.0, 1.0)), spec)
    ctx.part(tube(f"{ctx.title} knuckle glow {label}", [C + sv * x + k * 0.43 + f * 0.13 for x in (-0.36, 0.0, 0.36)],
                  [0.03, 0.034, 0.03], [M["magma"]], n=8, per=4), spec)
    thumb = [C - sv * side * 0.30 + k * 0.05 - f * 0.05, C - sv * side * 0.40 + k * 0.30 + f * 0.12,
             C - sv * side * 0.18 + k * 0.42 + f * 0.30]
    ctx.part(sweep(f"{ctx.title} thumb {label}", thumb, [0.12, 0.11, 0.08], [M["body"]], n=12, per=3, tile=2.0), spec)
    cuff = sweep(f"{ctx.title} gauntlet cuff {label}", [W - f * 0.12, W + f * 0.02, W + f * 0.16],
                 [0.43, 0.45, 0.48], [M["iron"]], n=24, per=2)
    ctx.part(finish(cuff, 0.03, 1, 0), rigid((f"Forearm.{label}", 0.3), (f"Hand.{label}", 0.7)))
    for t, mat, r, rad in ((0.16, M["trim"], 0.022, 0.51), (-0.12, M["trim"], 0.02, 0.46),
                           (0.02, M["glow"], 0.014, 0.48)):
        ring = [W + f * t + (sv * math.cos(q) + k * math.sin(q)) * rad for q in [i / 40 * TAU for i in range(40)]]
        ctx.part(trim(f"{ctx.title} cuff ring {label}{t}", ring, r, mat, closed=True),
                 rigid((f"Forearm.{label}", 0.3), (f"Hand.{label}", 0.7)))


# ===== 腿 =====
def build_legs(ctx, B, M):
    s = B.s
    for side, label in SIDES:
        L = B.legs[label]
        hip, knee, ankle = L["hip"], L["knee"], L["ankle"]
        leg = sweep(f"{ctx.title} leg {label}", [hip + Vector((-side * 0.05, 0, 0.30)), hip.lerp(knee, 0.4), knee,
                                                 knee.lerp(ankle, 0.45), ankle],
                    [0.54, 0.50, 0.42, 0.38, 0.32], [M["body"]], n=24, per=3, tile=3.2)
        ctx.part(leg, chain([f"Thigh.{label}", f"Shin.{label}", f"Foot.{label}"], "Pelvis", 0.16))
        cuisse(ctx, B, side, label, M["iron"], M["trim"], r=(0.225, 0.19), thick=0.03, trim_r=0.012)
        greave(ctx, B, side, label, M["iron"], M["trim"], r=(0.18, 0.148), thick=0.03, trim_r=0.012)
        # 护膝：前凸甲杯 + 金环 + 余烬宝石 + 前刺
        kspec = rigid((f"Thigh.{label}", 0.5), (f"Shin.{label}", 0.5))
        kc = knee + Vector((0, 0.34, 0.03))
        ctx.part(blob(f"{ctx.title} poleyn {label}", kc, (0.30, 0.17, 0.33), [M["iron"]], 22, 12, power=2.2), kspec)
        rim = [kc + Vector((math.sin(q) * 0.31, 0.06 - 0.10 * math.sin(q) ** 2, math.cos(q) * 0.34))
               for q in [i / 40 * TAU for i in range(40)]]
        ctx.part(trim(f"{ctx.title} poleyn rim {label}", rim, 0.018, M["trim"], closed=True), kspec)
        ctx.part(gem(f"{ctx.title} poleyn gem {label}", kc + Vector((0, 0.17, 0.12)), 0.05, M["glow"], (1, 0.6, 1.2)),
                 kspec)
        kn = kc + Vector((0, 0.12, -0.06))
        ctx.part(spike(f"{ctx.title} knee spike {label}", kn, kn + Vector((side * 0.05, 0.34, 0.10)), 0.09,
                       [M["gold"]], sides=6), kspec)
        for k in range(2):
            limb_plate(ctx, f"{ctx.title} tasset {label}{k}", hip + Vector((0, 0, (0.40 - k * 0.22))),
                       hip.lerp(knee, 0.45 - k * 0.12), 0.62 + k * 0.03, 0.56 + k * 0.03, M["iron"],
                       rigid(f"Thigh.{label}"), Vector((side, 0.3, 0)), arc=0.85, thick=0.03, trim_mat=M["trim"],
                       trim_r=0.012, rims=(1,))
        build_boot(ctx, B, M, side, label)


def build_boot(ctx, B, M, side, label):
    L = B.legs[label]
    ankle, ball, toe = L["ankle"], L["ball"], L["toe"]
    heel = Vector((ankle.x, ankle.y - 0.12, 0.26))
    boot = blob(f"{ctx.title} boot {label}", Vector((ankle.x, 0.14, 0.27)), (0.40, 0.62, 0.27), [M["iron"]], 26, 14,
                power=2.4, shape=lambda p: -0.10 * smoothstep(0.0, 0.25, p.z) * smoothstep(0.1, 0.6, p.y))
    ctx.part(boot, rigid(f"Foot.{label}"))
    cuff = sweep(f"{ctx.title} ankle guard {label}", [ankle + Vector((0, -0.02, -0.12)), ankle + Vector((0, 0, 0.30))],
                 [0.44, 0.38], [M["iron"]], n=22, per=1)
    ctx.part(finish(cuff, 0.03, 1, 0), rigid((f"Shin.{label}", 0.5), (f"Foot.{label}", 0.5)))
    ring = [ankle + Vector((math.sin(q) * 0.475, math.cos(q) * 0.475, 0.30)) for q in [i / 40 * TAU for i in range(40)]]
    ctx.part(trim(f"{ctx.title} ankle trim {label}", ring, 0.02, M["trim"], closed=True),
             rigid((f"Shin.{label}", 0.5), (f"Foot.{label}", 0.5)))
    cap = blob(f"{ctx.title} toe cap {label}", ball + Vector((0, 0.10, 0.10)), (0.36, 0.30, 0.14), [M["iron"]], 20, 10,
               power=2.3)
    ctx.part(cap, rigid(f"Toe.{label}"))
    for i, x in enumerate((-0.22, 0.0, 0.22)):
        base = ball + Vector((x, 0.30, 0.10))
        ctx.part(spike(f"{ctx.title} toe claw {label}{i}", base, base + Vector((x * 0.3, 0.30, -0.08)), 0.075,
                       [M["gold"]], sides=6, bend=0.04, up=(0, 0, 1)), rigid(f"Toe.{label}"))
    ctx.part(studs(f"{ctx.title} boot rivets {label}", [(Vector((ankle.x + x, 0.40, 0.48 - abs(x) * 0.3)),
                                                         (0, 0.6, 1), 0.035) for x in (-0.24, -0.08, 0.08, 0.24)],
                   [M["trim"]]), rigid(f"Foot.{label}"))


# ===== 胸甲、腰带、裙甲 =====
def build_armor(ctx, B, M):
    pec = lambda a, z: torso_shape(B, a, z) * 1.05   # noqa: E731
    shell(ctx, B, f"{ctx.title} cuirass", lambda a: 4.02 - 0.10 * max(0.0, math.cos(a)) ** 6,
          lambda a: 3.12 - 0.16 * max(0.0, math.cos(a)) ** 3, 0.06, M["iron"], invdist(["Spine", "Chest"], 0.3),
          a0=-1.55, a1=1.55, nu=48, nv=18, thick=0.035, trims=(M["trim"], 0.016), shape=pec)
    shell(ctx, B, f"{ctx.title} backplate", 3.95, 3.10, 0.05, M["iron"], invdist(["Spine", "Chest"], 0.3),
          a0=1.75, a1=TAU - 1.75, nu=30, nv=14, thick=0.03, trims=(M["trim"], 0.014),
          shape=lambda a, z: torso_shape(B, a, z))
    # 胸口熔炉心：金环、铁栅、熔岩玻璃
    core = B.on_torso(0, 3.55, 0.20)
    n = Vector((0, 1, 0.05)).normalized()
    disc = blob(f"{ctx.title} furnace heart", core + Vector((0, -0.02, 0)), (0.30, 0.06, 0.30), [M["magma"]], 28, 12)
    ctx.part(disc, invdist(["Spine", "Chest"], 0.3))
    ring = [core + Vector((math.sin(t) * 0.32, 0.03, math.cos(t) * 0.32)) for t in [i / 48 * TAU for i in range(48)]]
    ctx.part(trim(f"{ctx.title} heart ring", ring, 0.035, M["trim"], closed=True), invdist(["Spine", "Chest"], 0.3))
    ring2 = [core + Vector((math.sin(t) * 0.40, 0.0, math.cos(t) * 0.40)) for t in [i / 48 * TAU for i in range(48)]]
    ctx.part(trim(f"{ctx.title} heart ring outer", ring2, 0.022, M["trim"], closed=True),
             invdist(["Spine", "Chest"], 0.3))
    for k in range(8):
        t = k / 8 * TAU
        ctx.part(tube(f"{ctx.title} heart bar {k}", [core + Vector((math.sin(t) * 0.06, 0.05, math.cos(t) * 0.06)),
                                                     core + Vector((math.sin(t) * 0.31, 0.04, math.cos(t) * 0.31))],
                      [0.02, 0.024], [M["iron"]], n=6, per=1), invdist(["Spine", "Chest"], 0.3))
        tip = core + Vector((math.sin(t) * 0.40, 0.0, math.cos(t) * 0.40))
        ctx.part(spike(f"{ctx.title} heart ray {k}", tip, tip + Vector((math.sin(t), 0.05, math.cos(t))) *
                       (0.24 if k % 2 == 0 else 0.13), 0.045, [M["gold"]], sides=4, fx=1.0, fy=0.4, up=(0, 1, 0)),
                 invdist(["Spine", "Chest"], 0.3))
    ctx.part(gem(f"{ctx.title} heart gem", core + Vector((0, 0.07, 0)), 0.08, M["glow"], (1, 0.6, 1)),
             invdist(["Spine", "Chest"], 0.3))
    # 熔金锁链：两肩之间的胸前垂链 + 圆章
    for k, sag in enumerate((0.55, 0.85)):
        pts = []
        for i in range(13):
            t = i / 12
            x = lerp(-1.02, 1.02, t)
            z = 3.98 - sag * math.sin(math.pi * t) ** 1.2
            pts.append(B.on_torso(x * 0.97, z, 0.30 + 0.06 * math.sin(math.pi * t)))
        ctx.part(chain_links(f"{ctx.title} chest chain {k}", pts, 0.16, 0.022, [M["trim"]]), rigid("Chest"))
    # 腰带与熔炉扣
    shell(ctx, B, f"{ctx.title} belt", 2.84, 2.62, 0.07, M["gold"], invdist(["Pelvis", "Spine"], 0.3), nu=60, nv=5,
          thick=0.03, trims=(M["trim"], 0.014))
    buckle = B.on_torso(0, 2.73, 0.13)
    ctx.part(blob(f"{ctx.title} buckle", buckle, (0.30, 0.08, 0.24), [M["iron"]], 24, 10, power=2.6),
             rigid("Pelvis"))
    ctx.part(blob(f"{ctx.title} buckle glow", buckle + Vector((0, 0.05, 0)), (0.20, 0.05, 0.15), [M["magma"]], 20, 8),
             rigid("Pelvis"))
    for k in range(5):
        x = (k - 2) * 0.075
        ctx.part(tube(f"{ctx.title} buckle bar {k}", [buckle + Vector((x, 0.09, -0.14)), buckle + Vector((x, 0.09, 0.14))],
                      [0.016, 0.016], [M["trim"]], n=6, per=1), rigid("Pelvis"))
    for k, (zt, zb, g) in enumerate(((2.64, 2.38, 0.10), (2.44, 2.18, 0.14), (2.24, 1.98, 0.18))):
        shell(ctx, B, f"{ctx.title} fauld {k}", zt, lambda a, zb=zb: zb - 0.10 * max(0.0, -math.cos(a)) ** 2,
              g, M["iron"], rigid("Pelvis"), a0=0.95, a1=TAU - 0.95, nu=44, nv=6, thick=0.03,
              trims=(M["trim"], 0.013))


# ===== 炉墙（王座式背板，挂 Furnace 骨） =====
WALL_Y = -1.05
WALL_T = 0.34
WALL_HW = 1.30
ARCH_Z = 4.95
APEX = 6.50
ROSE_C = Vector((0, WALL_Y + WALL_T / 2 + 0.02, 5.32))
TOWERS = [(-1.52, 5.72), (1.52, 5.72)]
PINNACLES = [(-0.86, 6.02), (0.86, 6.02)]


def wall_bulge(x):
    return 0.22 * (x / WALL_HW) ** 2


def wall_hw(z):
    """炉墙半宽：直边到 ARCH_Z，之上是两段圆弧相交的哥特尖拱。"""
    if z <= ARCH_Z:
        return WALL_HW
    H = APEX - ARCH_Z
    Rr = (H * H + WALL_HW * WALL_HW) / (2 * WALL_HW)
    dz = min(H, z - ARCH_Z)
    return max(0.0, (WALL_HW - Rr) + math.sqrt(max(0.0, Rr * Rr - dz * dz)))


def wall_outline(n=14):
    pts = [(-WALL_HW, 3.30), (WALL_HW, 3.30)]
    zs = [ARCH_Z + (APEX - ARCH_Z) * math.sin(i / n * math.pi / 2) for i in range(n + 1)]
    pts += [(wall_hw(z), z) for z in zs[:-1]] + [(0.0, APEX)] + [(-wall_hw(z), z) for z in reversed(zs[:-1])]
    return pts


def build_furnace(ctx, M):
    spec_bone = "Furnace"
    # 板面用细分曲面（plate 是单个 n 边形，弧面只弯到轮廓，内部会盖住背面栅窗）
    def sp(u, v):
        z = lerp(APEX, 3.30, v)
        x = (2 * u - 1) * wall_hw(z)
        return Vector((x, WALL_Y + WALL_T / 2 - wall_bulge(x), z))

    def suv(u, v):
        p = sp(u, v)
        return ((p.x + WALL_HW) / 2.6, (p.z - 3.3) / 2.6)
    slab = surface(f"{ctx.title} furnace slab", sp, 26, 30, [M["brick"]], uvfn=suv)
    orient(slab, lambda c: Vector((c.x, -5.0, c.z)))
    ctx.attach(finish(slab, WALL_T, -1, 0, bev=0.02), spec_bone)
    outline = wall_outline()
    # 正面金色轮廓滚边 + 背面
    for sgn in (1, -1):
        edge = [Vector((x, WALL_Y + sgn * (WALL_T / 2 + 0.01) - wall_bulge(x), z)) for x, z in outline]
        ctx.attach(trim(f"{ctx.title} slab trim {sgn}", edge, 0.035, M["trim"], closed=True, per=1), spec_bone)
    # 玫瑰窗：熔岩玻璃圆盘 + 金色花窗格 + 铁辐条
    rc = ROSE_C
    ctx.attach(blob(f"{ctx.title} rose glass", rc + Vector((0, -0.01, 0)), (0.80, 0.04, 0.80), [M["magma"]], 36, 10),
               spec_bone)
    xa, za = Vector((1, 0, 0)), Vector((0, 0, 1))

    def at(th, r, dy=0.0):
        return rc + xa * math.sin(th) * r + za * math.cos(th) * r + Vector((0, dy, 0))
    for r, rad in ((0.84, 0.05), (0.62, 0.028), (0.30, 0.03), (0.12, 0.03)):
        ctx.attach(tube(f"{ctx.title} rose ring {r}", [at(i / 80 * TAU, r, 0.05) for i in range(80)], [rad] * 80,
                        [M["trim"]], n=8, closed=True, per=1), spec_bone)
    for k in range(12):
        th = k / 12 * TAU
        ctx.attach(tube(f"{ctx.title} rose spoke {k}", [at(th, 0.12, 0.05), at(th, 0.84, 0.05)], [0.022, 0.03],
                        [M["iron"]], n=6, per=1), spec_bone)
        petal = [at(th - 0.20, 0.34, 0.06), at(th, 0.60, 0.06), at(th + 0.20, 0.34, 0.06)]
        ctx.attach(tube(f"{ctx.title} rose petal {k}", petal, [0.016, 0.02, 0.016], [M["trim"]], n=6, per=4),
                   spec_bone)
        ctx.attach(spike(f"{ctx.title} rose ray {k}", at(th, 0.86, 0.03), at(th, 0.86 + (0.28 if k % 3 == 0 else 0.15), 0.03),
                         0.05, [M["gold"]], sides=4, fx=1.0, fy=0.45, up=(0, 1, 0)), spec_bone)
    ctx.attach(gem(f"{ctx.title} rose heart", rc + Vector((0, 0.08, 0)), 0.10, M["glow"], (1, 0.6, 1)), spec_bone)
    # 正面两扇尖拱熔炉栅窗（在头与肩之间透光）
    front_y = WALL_Y + WALL_T / 2 + 0.015
    for sd in (-1, 1):
        x0 = sd * 0.95
        win = [(x0 - 0.20, 3.75), (x0 + 0.20, 3.75), (x0 + 0.20, 4.45), (x0, 4.75), (x0 - 0.20, 4.45)]
        g = plate(f"{ctx.title} lancet glow {sd}", win, 0.03, [M["magma"]], origin=(0, front_y - 0.22 * (x0 / 1.3) ** 2, 0),
                  xaxis=(1, 0, 0), yaxis=(0, 0, 1))
        ctx.attach(g, spec_bone)
        for j in range(4):
            x = x0 - 0.15 + j * 0.10
            ctx.attach(tube(f"{ctx.title} lancet bar {sd}{j}", [(x, front_y + 0.03 - 0.22 * (x / 1.3) ** 2, 3.75),
                                                                (x, front_y + 0.03 - 0.22 * (x / 1.3) ** 2, 4.62)],
                            [0.018, 0.018], [M["iron"]], n=6, per=1), spec_bone)
        ol = [Vector((x, front_y + 0.03 - 0.22 * (x / 1.3) ** 2, z)) for x, z in win] + \
             [Vector((win[0][0], front_y + 0.03 - 0.22 * (win[0][0] / 1.3) ** 2, win[0][1]))]
        ctx.attach(trim(f"{ctx.title} lancet frame {sd}", ol, 0.025, M["trim"], closed=True, per=1), spec_bone)
    # 背面：三扇大栅窗 + 横向铁梁
    back_y = WALL_Y - WALL_T / 2 - 0.015
    for j, x0 in enumerate((-0.72, 0.0, 0.72)):
        top = 5.35 if j == 1 else 4.85
        win = [(x0 - 0.26, 3.55), (x0 + 0.26, 3.55), (x0 + 0.26, top - 0.35), (x0, top), (x0 - 0.26, top - 0.35)]
        yy = back_y - 0.22 * (x0 / 1.3) ** 2
        ctx.attach(plate(f"{ctx.title} rear grate {j}", win, 0.03, [M["magma"]], origin=(0, yy, 0), xaxis=(1, 0, 0),
                         yaxis=(0, 0, 1)), spec_bone)
        for i in range(5):
            x = x0 - 0.20 + i * 0.10
            ctx.attach(tube(f"{ctx.title} rear bar {j}{i}", [(x, yy - 0.035, 3.55), (x, yy - 0.035, top - 0.12)],
                            [0.02, 0.02], [M["iron"]], n=6, per=1), spec_bone)
        ol = [Vector((x, yy - 0.04, z)) for x, z in win] + [Vector((win[0][0], yy - 0.04, win[0][1]))]
        ctx.attach(trim(f"{ctx.title} rear frame {j}", ol, 0.03, M["trim"], closed=True, per=1), spec_bone)
    # 两侧烟囱塔（八棱柱、金箍、城垛帽）
    vents = []
    for k, (x, top) in enumerate(TOWERS):
        c = (x, WALL_Y - 0.05, 0)
        prof = [(0.20, top + 0.12), (0.34, top + 0.02), (0.34, top - 0.22), (0.24, top - 0.34), (0.26, 4.2),
                (0.30, 3.55), (0.36, 3.30)]
        tower = lathe(f"{ctx.title} chimney {k}", prof, [M["brick"]], segments=8, center=c)
        ctx.attach(auto_smooth(finish(tower, None, 1, 0, bev=0.01), 30), spec_bone)
        for zz, rr in ((top - 0.22, 0.36), (4.60, 0.28), (3.90, 0.30)):
            ring = [Vector((x + math.sin(q) * rr, WALL_Y - 0.05 + math.cos(q) * rr, zz)) for q in [i / 32 * TAU for i in range(32)]]
            ctx.attach(trim(f"{ctx.title} chimney band {k}{zz:.1f}", ring, 0.03, M["trim"], closed=True), spec_bone)
        for q in range(8):
            a = (q + 0.5) / 8 * TAU
            b0 = Vector((x + math.sin(a) * 0.30, WALL_Y - 0.05 + math.cos(a) * 0.30, top + 0.02))
            ctx.attach(spike(f"{ctx.title} merlon {k}{q}", b0, b0 + Vector((math.sin(a) * 0.05, math.cos(a) * 0.05, 0.22)),
                             0.06, [M["gold"]], sides=4), spec_bone)
        ctx.attach(blob(f"{ctx.title} chimney mouth {k}", Vector((x, WALL_Y - 0.05, top + 0.08)), (0.22, 0.22, 0.05),
                        [M["magma"]], 16, 6), spec_bone)
        vents.append((Vector((x, WALL_Y - 0.05, top + 0.06)), 0.95, 0.22))
    for k, (x, top) in enumerate(PINNACLES):
        base = Vector((x, WALL_Y, 5.0))
        ctx.attach(spike(f"{ctx.title} pinnacle {k}", base, Vector((x * 1.02, WALL_Y, top)), 0.16, [M["iron"]], sides=6),
                   spec_bone)
        for q in range(3):
            z = 5.25 + q * 0.22
            for sd in (-1, 1):
                b0 = Vector((x + sd * 0.12 * (1 - q * 0.25), WALL_Y, z))
                ctx.attach(spike(f"{ctx.title} crocket {k}{q}{sd}", b0, b0 + Vector((sd * 0.16, 0, 0.10)), 0.035,
                                 [M["gold"]], sides=4), spec_bone)
        ctx.attach(gem(f"{ctx.title} pinnacle gem {k}", Vector((x, WALL_Y + 0.16, 5.15)), 0.06, M["glow"], (0.8, 0.6, 1.4)),
                   spec_bone)
        vents.append((Vector((x * 1.02, WALL_Y, top - 0.10)), 0.55, 0.10))
    ctx.attach(spike(f"{ctx.title} apex spire", Vector((0, WALL_Y, APEX - 0.25)), Vector((0, WALL_Y, APEX + 0.45)), 0.10,
                     [M["gold"]], sides=6), spec_bone)
    vents.append((Vector((0, WALL_Y, APEX + 0.30)), 0.50, 0.08))
    # 余烬碎片（火舌周围悬浮）
    return vents


def build_vent_flames(ctx, M, vents):
    """背部排气口火舌：分层半透明火舌 + 悬浮火星（Vent 骨缩放时一起升高）+ 烧红喷口环（挂 Furnace 骨，保持稳定）。
    vents 的 (底点, 高, 半径) 沿用旧值；塔顶是烟囱，侧尖塔 / 顶尖是小喷口。"""
    for k, (base, h, r) in enumerate(vents):
        tower = r > 0.15
        f = FX.flame_bundle(f"{ctx.title} vent flame {k}", base, (0, 0, 1), h * (1.08 if tower else 1.12),
                            r * (1.10 if tower else 1.15), M["flame"], seed=k * 2.1 + 0.7,
                            n_out=4 if tower else 3, n_in=2, sparks=4 if tower else 2, spark_span=1.0)
        ctx.attach(f, f"Vent{k}")
        if tower:       # 烟囱口沿：喷口斜坡的上缘
            ring = FX.vent_ring(f"{ctx.title} vent ring glow {k}", base + Vector((0, 0, 0.065)), 0.215, 0.024, M["ring"])
        else:           # 尖塔 / 顶尖：火舌根部一圈烧红的小环
            ring = FX.vent_ring(f"{ctx.title} vent ring glow {k}", base + Vector((0, 0, 0.02)), 0.052, 0.011, M["ring"],
                                segs=16, n=5)
        ctx.attach(ring, "Furnace")


# ===== 披风（缝着锁链与余烬提灯） =====
def cloth():
    cape = Wrap("Cape", "Chest", math.pi - 1.30, math.pi + 1.30, top=lambda u: 3.58 - 0.10 * abs(math.sin((u - 0.5) * math.pi)),
                bottom=0.42, r_top=(1.10, 0.96), r_bot=(1.65, 1.30), K=6, cy=0.02,
                joints=(0, 0.16, 0.34, 0.52, 0.74, 1.0), flow=0.28, folds=(5.0, 0.02, 0.09), seed=1.7, tails=9,
                tail_len=(0.22, 0.14), curl=(0.08, 0.03), flare_exp=1.1, inset=0.03)
    loin = Panel("Loin", "Pelvis", 2.64, 1.02, [(0, 0.78), (0.5, 0.70), (1.0, 0.50)],
                 [(0, 0.72), (0.3, 0.80), (1.0, 0.86)], side=1, point=0.12, curve=0.5,
                 joints=(0, 0.30, 0.62, 1.0))
    return cape, loin


def build_cloth(ctx, M, cape, loin):
    cape.build(ctx, [M["cape"], M["lining"]], f"{ctx.title} cape", nu=90, nv=56, thickness=0.03, uv_scale=1.4,
               hem=(M["hem"], 0.022), edges=(M["trim"], 0.022))
    spec = garment(cape)
    # 三道垂链横挂在披风背面
    for k, v in enumerate((0.10, 0.30, 0.52)):
        pts = []
        for i in range(17):
            u = 0.06 + 0.88 * i / 16
            sag = 0.10 * math.sin(math.pi * ((u * 3) % 1.0))
            p = cape.point(u, v + sag * 0.35)
            pts.append(p + Vector((p.x, p.y - cape.cy, 0)).normalized() * 0.07)
        ctx.part(chain_links(f"{ctx.title} cape chain {k}", pts, 0.20, 0.028, [M["chain"]]), spec)
    # 竖挂链与余烬提灯
    for k, u in enumerate((0.16, 0.5, 0.84)):
        pts = []
        for i in range(10):
            v = 0.10 + 0.55 * i / 9
            p = cape.point(u, v)
            pts.append(p + Vector((p.x, p.y - cape.cy, 0)).normalized() * 0.10)
        ctx.part(chain_links(f"{ctx.title} cape drop {k}", pts, 0.20, 0.028, [M["chain"]]), spec)
        end = pts[-1] + Vector((0, 0, -0.18))
        ctx.part(blob(f"{ctx.title} lantern core {k}", end, (0.12, 0.12, 0.17), [M["glow"]], 14, 10), spec)
        for q in range(6):
            a = q / 6 * TAU
            ctx.part(tube(f"{ctx.title} lantern bar {k}{q}", [end + Vector((math.sin(a) * 0.05, math.cos(a) * 0.05, 0.26)),
                                                              end + Vector((math.sin(a) * 0.16, math.cos(a) * 0.16, 0.0)),
                                                              end + Vector((math.sin(a) * 0.05, math.cos(a) * 0.05, -0.26))],
                          [0.018, 0.022, 0.018], [M["trim"]], n=5, per=3), spec)
    loin.build(ctx, [M["cape"], M["lining"]], f"{ctx.title} loin banner", nu=20, nv=40, thickness=0.03,
               edges=(M["trim"], 0.02), spine=(M["hem"], 0.012))


# ===== 构建 =====
def build(ctx):
    M = materials(ctx)
    B = giant_body()
    build_torso(ctx, B, M)
    build_armor(ctx, B, M)
    build_head(ctx, B, M)
    tips = [(t, L, tall) for t, L, tall in build_crown_tips()]
    build_crown_flames(ctx, M, tips)
    build_halo(ctx, M)
    build_arms(ctx, B, M)
    build_legs(ctx, B, M)
    vents = build_furnace(ctx, M)
    build_vent_flames(ctx, M, vents)
    cape, loin = cloth()
    build_cloth(ctx, M, cape, loin)
    bbox_report(ctx.id, [o for o, _ in ctx.parts] + [o for o, *_ in ctx.attached])
    return {"B": B, "tips": tips, "vents": vents, "cape": cape, "loin": loin,
            "fist_pts": {}}


def build_crown_tips():
    out = []
    for k in range(8):
        a = k / 8 * TAU
        tall = k % 2 == 0
        L = 0.64 if k == 0 else (0.52 if tall else 0.30)
        base = crown_point(a, 1.0, 0.08)
        out.append((base + Vector((math.sin(a) * 0.12, math.cos(a) * 0.12, L)), L, tall))
    return out


# ===== 骨骼 =====
def skeleton(rig, st):
    B = st["B"]
    rig.bone("Root", (0, 0, 0), (0, 0, 0.5))
    rig.bone("Hover", (0, 0, 0.5), (0, 0, 1.0), "Root")
    rig.translate["Hover"] = "_hover"
    rig.bone("Pelvis", (0, 0, B.pelvis_z), (0, 0.02, B.waist_z), "Hover", roll=Y)
    rig.bone("Spine", (0, 0.02, B.waist_z), (0, 0.06, B.chest_z), "Pelvis", roll=Y)
    rig.bone("Chest", (0, 0.06, B.chest_z), (0, 0.06, B.neck_base), "Spine", roll=Y)
    rig.bone("Neck", (0, 0.10, B.neck_base - 0.08), (0, 0.28, B.chin + 0.06), "Chest", roll=Y)
    rig.bone("Head", (0, 0.28, B.chin + 0.06), (0, 0.34, B.head_top), "Neck", roll=Y)
    for side, label in SIDES:
        a = B.arms[label]
        rig.bone(f"UpperArm.{label}", a["shoulder"], a["elbow"], "Chest", roll=Y)
        rig.bone(f"Forearm.{label}", a["elbow"], a["wrist"], f"UpperArm.{label}", roll=Y)
        f, k, sv = fist_frame(B, label)
        rig.bone(f"Hand.{label}", a["wrist"], a["wrist"] + f * 0.45, f"Forearm.{label}", roll=k)
        L = B.legs[label]
        rig.bone(f"Thigh.{label}", L["hip"], L["knee"], "Pelvis", roll=Y)
        rig.bone(f"Shin.{label}", L["knee"], L["ankle"], f"Thigh.{label}", roll=Y)
        rig.bone(f"Foot.{label}", L["ankle"], L["ball"], f"Shin.{label}", roll=Z)
        rig.bone(f"Toe.{label}", L["ball"], L["toe"], f"Foot.{label}", roll=Z)
    rig.bone("Halo", HALO_C, HALO_C + Vector((0, 0, 0.3)), "Head", roll=Y)
    rig.translate["Halo"] = "_halo"
    for k, (tip, L, tall) in enumerate(st["tips"]):
        base = tip - Vector((0, 0, 0.08))
        rig.bone(f"Flare{k}", base, base + Vector((0, 0, 0.25)), "Head", roll=Y)
    rig.bone("Furnace", (0, WALL_Y, 3.40), (0, WALL_Y, 4.40), "Chest", roll=Y)
    for k, (base, h, r) in enumerate(st["vents"]):
        rig.bone(f"Vent{k}", base, base + Vector((0, 0, h)), "Furnace", roll=Y)
    rig.add_garment(st["cape"])
    rig.add_garment(st["loin"])
    rig.scaled = [f"Flare{k}" for k in range(len(st["tips"]))] + [f"Vent{k}" for k in range(len(st["vents"]))]


# ===== 动作 =====
def rest_pole(B, label):
    a = B.arms[label]
    S, E, W = a["shoulder"], a["elbow"], a["wrist"]
    d = (W - S).normalized()
    p = E - S
    return (p - d * p.dot(d)).normalized()


def grow(h):
    """火舌骨缩放：高度（骨局部 Y）按倍率拉伸，宽度只随之涨一半——爆燃时是“窜高”而不是整体变胖。"""
    w = 1 + 0.50 * (h - 1)
    return (w, h, w)


def flames(rig, pose, st, t=0.0, vent=1.0, crown=1.0, flicker=0.12, drift=(0.0, 0.0)):
    """火焰：缩放通道做爆燃 / 闪烁；火焰骨每帧重新指向世界上方（身体前倾时火舌仍向上窜），drift 为风向偏移。"""
    sc = {}
    for k in range(len(st["vents"])):
        sc[f"Vent{k}"] = grow(vent * (1 + flicker * math.sin(3 * t + k * 1.7)))
        d = Vector((drift[0] + 0.06 * math.sin(2 * t + k), drift[1] + 0.05 * math.cos(3 * t + k * 0.7), 1.0))
        rig.aim(pose, f"Vent{k}", d)
    for k in range(len(st["tips"])):
        sc[f"Flare{k}"] = grow(crown * (1 + flicker * 0.8 * math.sin(2 * t + k * 2.3)))
        d = Vector((drift[0] + 0.05 * math.sin(2 * t + k * 1.3), drift[1] + 0.05 * math.cos(2 * t + k), 1.0))
        rig.aim(pose, f"Flare{k}", d)
    pose["_scale"] = sc


def arms_ik(rig, B, pose, targets, poles):
    for label in ("L", "R"):
        rig.ik2(pose, f"UpperArm.{label}", f"Forearm.{label}", targets[label], poles[label],
                rest_pole=rest_pole(B, label))


def cape_idle(rig, st, t, pose, amp=1.0, back=0.03):
    rig.wind(pose, st["cape"], lambda k, j: (back + 0.02 * math.sin(t + k * 0.8 + j * 0.9)) * amp,
             lambda k, j: 0.03 * amp, lambda k, j: 0.012 * math.sin(t + k * 0.9 + j * 0.6) * amp)


def loin_clear(rig, st, pose, extra=0.0):
    """前腰旗按膝盖前移量外掀，避免屈膝时膝甲穿出旗面。"""
    loin = st["loin"]
    need = 0.04
    for label in ("L", "R"):
        knee = rig.tail(pose, f"Thigh.{label}")
        depth = loin.depth(0.5)
        dz = max(0.4, loin._top - knee.z)
        need = max(need, math.atan2(knee.y + 0.45 - depth, dz))
    rig.garment_pose(pose, loin, lambda k, j: need + extra)


def idle_pose(rig, st, t):
    B = st["B"]
    p = {}
    p["_hover"] = -0.05 + 0.02 * math.sin(t)
    p["Pelvis"] = R((Y, 0.012 * math.sin(t)))
    p["Spine"] = R((X, -0.02 * math.sin(t + 0.6)))
    p["Chest"] = R((X, 0.03 * math.sin(t + 0.9)), (Y, -0.01 * math.sin(t)))
    p["Neck"] = R((X, -0.02 + 0.02 * math.sin(t + 1.4)))
    p["Head"] = R((X, -0.02 + 0.03 * math.sin(t + 1.8)), (Z, 0.06 * math.sin(t)))
    for label, sg in (("L", -1), ("R", 1)):
        p[f"UpperArm.{label}"] = R((Y, sg * 0.03 * math.sin(t + 0.4)), (X, 0.05 + 0.03 * math.sin(t + 0.8)))
        p[f"Forearm.{label}"] = R((X, 0.10 + 0.04 * math.sin(t + 1.2)))
        p[f"Hand.{label}"] = R((X, 0.05 * math.sin(t + 1.6)))
    Legs(rig, B).stand(p, 0.0, 0.1, yaw=0.10)
    p["Halo"] = R((Z, -t))
    cape_idle(rig, st, t, p)
    loin_clear(rig, st, p)
    flames(rig, p, st, t * 2, flicker=0.06)     # 待机：火舌小而稳，闪烁幅度减半
    return p


def impact(d, w=0.07):
    """落脚冲击脉冲：d 为距离落脚的相位（0..1，周期），落脚后略滞后达到峰值。"""
    d = d - 0.03
    return math.exp(-(d / w) ** 2) + math.exp(-((d - 1) / w) ** 2) + math.exp(-((d + 1) / w) ** 2)


def move_pose(rig, st, t):
    """重步：脚掌放平抬起、前送、整脚砸地（kit.gait 的踮脚俯仰按人类脚长设计，巨人长脚会把脚趾压进地面）。"""
    B = st["B"]
    legs = Legs(rig, B)
    p = {}
    stride, lift, stance = 0.95, 0.40, 0.60
    shock = 0.0
    for label, ph in (("L", 0.0), ("R", 0.5)):
        side = -1 if label == "L" else 1
        q = (t / TAU + ph) % 1.0
        if q < stance:
            s = q / stance
            dy, dz, pitch = stride * (0.5 - s), 0.0, 0.0
        else:
            s = (q - stance) / (1 - stance)
            e = s * s * (3 - 2 * s)
            dy = stride * (-0.5 + e)
            dz = lift * math.sin(math.pi * s) ** 0.8
            pitch = -0.22 * math.sin(math.pi * s) + 0.10 * math.sin(math.pi * s) ** 4
        shock += impact(q)
        a = legs.rest[label]["ankle"] + Vector((side * 0.02, dy, dz))
        legs_p = (label, a, pitch, side)
        p.setdefault("_legs", []).append(legs_p)
    sway = -0.13 * math.cos(t - 0.6 * math.pi)
    p["_hover"] = Vector((sway, 0, -0.10 - 0.10 * shock + 0.045 * math.cos(2 * t - 0.6)))
    p["Pelvis"] = R((Z, 0.10 * math.sin(t - 0.6 * math.pi)), (Y, 0.05 * math.cos(t - 0.6 * math.pi)), (X, -0.08))
    p["Spine"] = R((Z, -0.06 * math.sin(t - 0.6 * math.pi)), (X, -0.04 - 0.03 * shock))
    p["Chest"] = R((Z, -0.07 * math.sin(t - 0.6 * math.pi)), (X, 0.02 * shock), (Y, -0.03 * math.cos(t - 0.6 * math.pi)))
    p["Neck"] = R((X, 0.06 + 0.03 * shock))
    p["Head"] = R((X, 0.04), (Z, 0.05 * math.sin(t - 0.6 * math.pi)))
    for label, a, pitch, side in p.pop("_legs"):
        legs.plant(p, label, a, pitch=pitch, yaw=-side * 0.10, knee_out=0.25)
    for label, ph in (("L", 0.6 * math.pi), ("R", 1.6 * math.pi)):
        side = -1 if label == "L" else 1
        sw = math.cos(t - ph)
        p[f"UpperArm.{label}"] = R((X, 0.30 * sw), (Y, side * (0.05 + 0.03 * shock)))
        p[f"Forearm.{label}"] = R((X, 0.30 + 0.18 * max(0.0, sw)))
        p[f"Hand.{label}"] = R((X, 0.12 * sw))
    p["Halo"] = R((Z, -t))
    rig.wind(p, st["cape"], lambda k, j: 0.10 + 0.04 * math.sin(2 * t + k * 0.7 + j * 1.1) - 0.03 * shock,
             lambda k, j: 0.03 + 0.03 * shock, lambda k, j: 0.03 * math.sin(t + k * 0.6 + j * 0.8))
    loin_clear(rig, st, p, 0.03 * math.sin(2 * t + 0.5))
    flames(rig, p, st, t * 3, vent=1.05 + 0.25 * shock, drift=(0.0, -0.22))
    return p


def fist_samples(st, label):
    """拳头外轮廓采样点（静止姿态），用于求姿态下拳头最低点。"""
    B = st["B"]
    W = B.arms[label]["wrist"]
    f, k, sv = fist_frame(B, label)
    C = W + f * 0.40
    return [C + f * 0.44, C + k * 0.52 + f * 0.30, C - k * 0.40, C + sv * 0.40, C - sv * 0.40,
            C + k * 0.40 + f * 0.40, C + f * 0.30 + sv * 0.30, C + f * 0.30 - sv * 0.30]


def fist_low(rig, st, pose, label):
    name = f"Hand.{label}"
    h0 = rig.SEG[name][0]
    h = rig.head(pose, name)
    d = rig.delta(pose, name)
    return min((h + d @ (p - h0)).z for p in st["fist_pts"][label])


def pose_from(rig, st, q, t=0.0):
    """由关键参数生成姿态（每帧重算腿 / 臂 IK，脚始终钉地）：
    sink 下蹲、lean 前倾（负为后仰）、arch 挺胸、head 抬头、fist.L/R 腕目标、pole.L/R 肘朝向、
    ground 拳头贴地权重（1 时把腕目标下压到拳底触地）、vent/crown 火焰倍率、halo 光环累计转角、lift 光环升起。"""
    B = st["B"]
    p = {}
    p["_hover"] = -q["sink"]
    lean, tw = q["lean"], q["twist"]
    p["Pelvis"] = R((X, -lean * 0.35), (Z, tw * 0.4))
    p["Spine"] = R((X, -lean * 0.30), (Z, tw * 0.3))
    p["Chest"] = R((X, -lean * 0.35 - q["arch"]), (Z, tw * 0.3))
    p["Neck"] = R((X, q["head"] * 0.5))
    p["Head"] = R((X, q["head"] * 0.5), (Y, q["shake"]))
    legs = Legs(rig, B)
    for label in ("L", "R"):
        side = -1 if label == "L" else 1
        legs.plant(p, label, legs.rest[label]["ankle"], yaw=-side * 0.10, knee_out=0.25)
    targets = {"L": Vector(q["fist.L"]), "R": Vector(q["fist.R"])}
    poles = {"L": q["pole.L"], "R": q["pole.R"]}
    for label in ("L", "R"):
        p[f"Hand.{label}"] = R((X, q[f"wrist.{label}"]))
    reach = rig.LEN["UpperArm.L"] + rig.LEN["Forearm.L"]
    for _ in range(4):
        arms_ik(rig, B, p, targets, poles)
        for label in ("L", "R"):
            low = fist_low(rig, st, p, label)
            want = 0.02
            if low < want:
                targets[label].z += want - low
            elif q["ground"] > 0:
                targets[label].z -= (low - want) * q["ground"]
            # 目标超出臂长时，保持高度、把水平分量收回（拳头优先贴地）
            S = rig.head(p, f"UpperArm.{label}")
            v = targets[label] - S
            lim = reach * 0.985
            if v.length > lim:
                h = Vector((v.x, v.y, 0))
                vz = max(-lim, min(lim, v.z))
                hl = math.sqrt(max(0.0, lim * lim - vz * vz))
                if h.length > 1e-6:
                    h = h.normalized() * min(h.length, hl)
                targets[label] = S + h + Vector((0, 0, vz))
    arms_ik(rig, B, p, targets, poles)
    p["Halo"] = R((Z, -q["halo"]))
    p["_halo"] = Vector((0, 0, q["lift"]))
    # 披风按躯干前倾量反向回摆，保持垂坠（不随上身一起翘起）
    tilt = lean + q["arch"]
    rig.wind(p, st["cape"], lambda k, j: q["cape"] - 0.46 * tilt + 0.02 * math.sin(t + k * 0.8 + j * 0.9),
             lambda k, j: 0.03 + q["flare"], lambda k, j: 0.012 * math.sin(t + k * 0.9 + j * 0.6))
    loin_clear(rig, st, p, -0.3 * max(0.0, -tilt))
    flames(rig, p, st, t, vent=q["vent"], crown=q["crown"], flicker=0.10)
    return p


def neutral_params(rig, st):
    """与 Idle 首帧一致的中性参数：腕目标取 Idle 首帧的腕位，肘朝向取静止肘向。"""
    B = st["B"]
    p0 = idle_pose(rig, st, 0.0)
    return {"sink": 0.05, "lean": 0.0, "arch": 0.0, "head": -0.04, "halo": 0.0, "vent": 1.0, "crown": 1.0,
            "cape": 0.03, "twist": 0.0, "shake": 0.0, "ground": 0.0, "lift": 0.0, "flare": 0.0,
            "fist.L": rig.tail(p0, "Forearm.L"), "fist.R": rig.tail(p0, "Forearm.R"),
            "pole.L": rest_pole(B, "L"), "pole.R": rest_pole(B, "R"), "wrist.L": 0.0, "wrist.R": 0.0}


def attack_keys(rig, st):
    """双拳砸地：1 起势 → 5 下沉蓄力 → 11 双拳高举（V 形）→ 14 顶点 → 17 砸地 → 21 冲击停顿 → 26 起身 → 33 收势。"""
    base = neutral_params(rig, st)
    dip = {"sink": 0.16, "lean": 0.10, "head": -0.10,
           "fist.L": Vector((-2.05, -0.10, 2.20)), "fist.R": Vector((2.05, -0.10, 2.20)), "vent": 0.85}
    up = {"sink": -0.06, "lean": -0.22, "arch": 0.10, "head": 0.26,
          "fist.L": Vector((-1.38, 0.45, 5.88)), "fist.R": Vector((1.38, 0.45, 5.88)),
          "pole.L": Vector((-1, -0.3, -0.2)), "pole.R": Vector((1, -0.3, -0.2)), "wrist.L": -0.35, "wrist.R": -0.35,
          "vent": 1.3, "crown": 1.2, "halo": 0.6, "cape": 0.02, "lift": 0.25}
    apex = dict(up, sink=-0.10, lean=-0.28, head=0.32, halo=0.9, lift=0.35,
                **{"fist.L": Vector((-1.34, 0.32, 6.02)), "fist.R": Vector((1.34, 0.32, 6.02))})
    slam = {"sink": 0.48, "lean": 0.88, "arch": 0.0, "head": 0.05, "ground": 1.0,
            "fist.L": Vector((-0.55, 1.75, 0.80)), "fist.R": Vector((0.55, 1.75, 0.80)),
            "pole.L": Vector((-1, -0.2, 0.5)), "pole.R": Vector((1, -0.2, 0.5)), "wrist.L": 0.30, "wrist.R": 0.30,
            "vent": 2.1, "crown": 1.6, "halo": 1.8, "cape": 0.10, "flare": 0.10, "lift": 0.0}
    hold = dict(slam, sink=0.46, lean=0.84, vent=1.8, crown=1.45, halo=2.1, cape=0.06, flare=0.06, shake=0.05)
    rise = dict(hold, sink=0.22, lean=0.35, vent=1.4, halo=2.6, cape=0.04, flare=0.0, shake=0.0, ground=0.0,
                **{"fist.L": Vector((-1.2, 1.2, 1.9)), "fist.R": Vector((1.2, 1.2, 1.9))})
    end = dict(base, halo=math.pi)
    return with_defaults(base, [(1, {}, "io"), (5, dip, "io"), (11, up, "io"), (14, apex, "out"), (17, slam, "in"),
                                (21, hold, "out"), (26, rise, "io"), (33, end, "io")])


def enrage_keys(rig, st):
    """咆哮：1 → 10 收拳蓄力（火焰内敛）→ 17 仰天展臂（爆燃、光环升起）→ 24/34 持续咆哮 → 44 回落 → 49 收势。"""
    base = neutral_params(rig, st)
    gather = {"sink": 0.30, "lean": 0.30, "head": -0.25, "arch": 0.0,
              "fist.L": Vector((-0.95, 1.65, 3.05)), "fist.R": Vector((0.95, 1.65, 3.05)),
              "pole.L": Vector((-1, -0.4, -0.3)), "pole.R": Vector((1, -0.4, -0.3)), "wrist.L": 0.4, "wrist.R": 0.4,
              "vent": 0.7, "crown": 0.8, "halo": 0.5, "cape": 0.05}
    roar = {"sink": -0.05, "lean": -0.34, "arch": 0.16, "head": 0.55,
            "fist.L": Vector((-2.85, 0.55, 5.05)), "fist.R": Vector((2.85, 0.55, 5.05)),
            "pole.L": Vector((-0.3, -1, -0.6)), "pole.R": Vector((0.3, -1, -0.6)), "wrist.L": -0.3, "wrist.R": -0.3,
            "vent": 2.4, "crown": 1.9, "halo": 3.0, "cape": 0.12, "flare": 0.12, "lift": 0.45}
    roar2 = dict(roar, halo=5.5, vent=2.6, crown=2.0, head=0.60, lift=0.55,
                 **{"fist.L": Vector((-2.90, 0.45, 5.20)), "fist.R": Vector((2.90, 0.45, 5.20))})
    roar3 = dict(roar2, halo=9.5)
    settle = dict(base, halo=12.3, vent=1.3, crown=1.15, lift=0.08)
    end = dict(base, halo=2 * TAU)
    return with_defaults(base, [(1, {}, "io"), (10, gather, "io"), (17, roar, "back"), (24, roar2, "out"),
                                (34, roar3, "lin"), (44, settle, "io"), (49, end, "io")])


def animate(rig, st):
    st["fist_pts"] = {label: fist_samples(st, label) for label in ("L", "R")}
    loop(rig, "Idle", 96, lambda t: idle_pose(rig, st, t), step=2)
    loop(rig, "Move", 48, lambda t: move_pose(rig, st, t), step=1)
    ak = attack_keys(rig, st)
    lows = []

    def attack(f):
        p = pose_from(rig, st, track(ak, f), f * 0.6)
        lows.append((min(fist_low(rig, st, p, lb) for lb in "LR"), f))
        return p
    sampled(rig, "Attack", 32, attack)
    lo = min(lows)
    print(f"MOTION CHECK+ Attack: fist lowest point {lo[0]:.3f} m at frame {lo[1]} (contact frames "
          f"{[f for z, f in lows if z < 0.05]})")
    ek = enrage_keys(rig, st)

    def enrage(f):
        q = track(ek, f)
        if 17 <= f <= 38:                          # 咆哮震颤
            amp = smoothstep(17, 20, f) * (1 - smoothstep(34, 38, f))
            q["shake"] += 0.035 * math.sin(f * 2.1) * amp
            q["lean"] += 0.02 * math.sin(f * 1.7) * amp
        return pose_from(rig, st, q, f * 0.9)
    sampled(rig, "Enrage", 48, enrage)
    ground_check(rig, CLIPS, [f"Toe.{s}" for s in "LR"] + [f"Foot.{s}" for s in "LR"], "foot bone", offset=0.0)
    seam_check(rig, ("Idle", "Move"))
