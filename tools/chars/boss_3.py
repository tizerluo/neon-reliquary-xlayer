"""Boss 3 · 空壳元帅 · 亡灵主机（The Hollow Marshal · Undead Mainframe）。

设定：约 5.5 m 的骷髅将军（颅顶 5.5 m，王冠尖刺 / 军旗再向上）。粗壮的骨架外覆骨白瓷釉与暗金重甲——分层肩甲（金顶三尖刺、
四层象牙 / 金 / 黑漆叠壳、发光纹章）、只包肋笼外缘的叠片胸甲（前方留窗，露出肋骨与心核）、尖齿腰裙、人字尖腿甲、
尖刺膝甲、铁靴；肋笼里是多层“服务器心核”（心脏模块 + 四个抽屉 + 线缆），肋骨后有发光背板；
狭长头骨（斜眼眶里燃着半透明淡紫幽火、獠牙、重下颌、锐利颧弓）戴王冠盔（御冠拱 + 两层节奏尖刺 + 眉甲 + 颊翼 + 后颈甲片 + 盔顶幽焰）；
背后军旗架（中桅穿过斗篷背缝）竖起三面扇形燕尾军旗（骨链旗布，王冠骷髅纹章，杆顶饰是微型王冠笼）；
右手握旗枪（燕尾旗是三节骨链布料）；破烂幽灵斗篷（内外两层、撕裂下摆条带、破洞、背中撕缝、撕口淡紫微光）。
配色：骨白、暗金、深紫、淡紫冷光。
动作：Idle（沉稳呼吸，旗面轻拂）/ Move（行军重步）/ Attack（举旗枪横扫 → 召唤）/ Enrage（军旗展开、幽光大盛）。
本配方的私有辅助：_b3_lib.py（贴图、半透明幽火、破烂斗篷、步态、检查）、_b3_shots.py（审图取景）。
"""

import math

from mathutils import Matrix, Vector

from kit.core import (TAU, apply_all, circuit_maps, ellipsoid, filigree_maps, finish, frame_from, garment, interp, invdist, lerp, orient,
                      plate, projector, rigid, ring_points as _ring_points, smoothstep, solidify, spike, surface, transform, tube)
from kit.garment import Panel
from kit.humanoid import SIDES, Body, add_skeleton, hand, limb_frame, limb_plate, poleyn, sabaton, shell
from kit.motion import Legs, fingers
from kit.rig import R, X, Y, Z

from chars._b3_lib import (Banner, RaggedCape, tabard_maps, ragged_hem, banner_maps, bbox_report, bone_maps, box, chain_links, clamp_ground, drawer,
                           flame_maps, flame_material, flame_sheets, gait_b3, ground_check, loop, rack_maps, sampled, seam_check,
                           thin_trims, track, tri_report, wisp_maps, with_defaults)

def gem(name, center, size, mat, stretch=(1.0, 0.6, 1.4)):
    """低面数宝石（8×6 椭球）：发光 / 嵌线 / 滚边材质不参与游戏版减面，小件必须从源头省面。"""
    return ellipsoid(name, center, (size * stretch[0], size * stretch[1], size * stretch[2]), [mat], 8, 6)


def trim(name, points, radius, mat, closed=False, n=5, per=1):
    """五边截面的细管（kit 默认六边）：滚边同样不参与减面。"""
    return tube(name, points, [radius] * len(points), [mat], n=n, closed=closed, per=per)


def ring_points(center, normal, radius, count, phase=0.0):
    """圆环取点（点数 ×0.7，下限 10）：滚边环不参与游戏版减面，14 边对半径 ≤ 0.2 m 的小环已足够圆。"""
    return _ring_points(center, normal, radius, max(10, int(count * 0.7)), phase)


TITLE = "Hollow Marshal"
ACCENT = (0.80, 0.67, 1.0)
CLIPS = ("Idle", "Move", "Attack", "Enrage")
GAME_TRIS = 85000
LOD_KEEP = ("inlay", "glow", "hem", "trim", "core", "flame", "void")
REVIEW_POSE = ("Idle", 1)
LAV = ACCENT
GLOW = (0.58, 0.42, 1.0)        # 发光色取饱和一些，AgX 下呈淡紫而不是发白
HEIGHT = 5.3
HAND_SC = 1.40
HEAD_SCALE = 1.12

# 躯干（肋笼）截面：kz 为身高单位，(rx, ry, 前后偏移)
TORSO = [(1.06, (0.138, 0.102, -0.012)), (1.14, (0.152, 0.108, -0.012)), (1.22, (0.130, 0.096, -0.020)),
         (1.30, (0.150, 0.106, -0.010)), (1.36, (0.178, 0.118, 0.000)), (1.44, (0.200, 0.128, 0.005)),
         (1.52, (0.208, 0.132, 0.008)), (1.59, (0.198, 0.126, 0.006)), (1.645, (0.168, 0.108, 0.000)),
         (1.68, (0.100, 0.078, -0.004)), (1.72, (0.062, 0.058, 0.000))]


# ===== 材质 =====
def materials(ctx):
    M = ctx.M
    ctx.mat("bone", "aged ivory bone", (0.62, 0.56, 0.44), rough=0.55, coat=0.1, spec=0.4)
    ctx.texture("bone", bone_maps(base_rgb=(0.62, 0.56, 0.44), emit_rgb=GLOW, size=1024, seed=5), emit_strength=1.6,
                normal_strength=0.8)
    ctx.mat("plate", "pale enamel plate", (0.80, 0.77, 0.70), metal=0.30, rough=0.24, coat=0.9)
    ctx.texture("plate", filigree_maps((0.80, 0.77, 0.70), (0.34, 0.28, 0.44), emit_rgb=(0.50, 0.34, 1.0), size=1024,
                                       seed=8, density=6, width=2), emit_strength=0.9, normal_strength=0.55)
    ctx.mat("gold", "dark gold", (0.52, 0.38, 0.16), metal=1.0, rough=0.30)
    ctx.texture("gold", filigree_maps((0.52, 0.38, 0.16), (0.24, 0.15, 0.06), size=1024, seed=14, density=18,
                                      width=1), normal_strength=0.5)
    ctx.mat("trim", "dark gold trim", (0.62, 0.46, 0.20), metal=1.0, rough=0.24)
    ctx.mat("cape", "spectral shroud", (0.050, 0.030, 0.100), rough=0.62, sheen=0.5,
            sheen_tint=(0.62, 0.45, 1.0), spec=0.12)
    ctx.texture("cape", wisp_maps(GLOW, base_rgb=(0.050, 0.030, 0.100), size=1024, seed=19, rune_rows=(240, 300)),
                emit_strength=2.2,
                normal_strength=0.4)
    ctx.mat("lining", "deep purple satin lining", (0.060, 0.034, 0.120), rough=0.55, sheen=0.4, sheen_tint=(0.62, 0.45, 1.0), spec=0.15)
    ctx.mat("banner", "war banner silk", (0.045, 0.020, 0.095), rough=0.62, sheen=0.35, sheen_tint=(0.62, 0.45, 1.0), spec=0.15)
    ctx.texture("banner", banner_maps((0.50, 0.37, 0.15), GLOW, base_rgb=(0.045, 0.020, 0.095), w=512, h=832, seed=23),
                emit_strength=2.0, normal_strength=0.4)
    ctx.mat("tabard", "war tabard silk", (0.045, 0.020, 0.095), rough=0.62, sheen=0.35, sheen_tint=(0.62, 0.45, 1.0), spec=0.15)
    ctx.texture("tabard", tabard_maps((0.50, 0.37, 0.15), GLOW, base_rgb=(0.045, 0.020, 0.095), w=256, h=1024, seed=31),
                emit_strength=2.0, normal_strength=0.4)
    ctx.mat("haft", "black violet lacquer", (0.030, 0.020, 0.045), metal=0.5, rough=0.25, coat=0.8)
    ctx.texture("haft", circuit_maps(GLOW, base_rgb=(0.030, 0.020, 0.050), size=1024, seed=41, buses=11, reach=(0.45, 1.0),
                                     fade=False), emit_strength=1.3, normal_strength=0.3)
    ctx.mat("core", "mainframe chassis core", (0.045, 0.045, 0.065), metal=0.85, rough=0.30)
    ctx.texture("core", rack_maps(GLOW, size=512, units=4, seed=29), emit_strength=4.6, normal_strength=0.6)
    ctx.mat("glow", "soul light glow", (0.70, 0.58, 1.0), emit=GLOW, strength=3.8)
    ctx.mat("heart", "soul core heart glow", (0.50, 0.30, 1.0), emit=(0.46, 0.22, 1.0), strength=2.2)
    ctx.mat("backlight", "ghost backlight glow", (0.35, 0.20, 0.80), emit=(0.40, 0.20, 1.0), strength=1.5)
    ctx.mat("inlay", "spectral inlay", (0.45, 0.36, 0.70), emit=GLOW, strength=2.2)
    ctx.mat("hem", "ghost hem light", (0.40, 0.26, 0.80), emit=(0.46, 0.26, 1.0), strength=2.0)
    ctx.mat("void", "socket void", (0.004, 0.003, 0.008), rough=0.9, spec=0.1)
    # 幽火：半透明薄片材质（RGBA 贴图：外焰深紫、内焰近白），alpha 向尖端 / 边缘渐隐
    M["flame"] = flame_material(f"{ctx.title} ghost fire flame", flame_maps(128, seed=3), 3.0)
    M["flamehot"] = flame_material(f"{ctx.title} ghost fire flame core",
                                   flame_maps(128, seed=9, core=1.7, edge=(0.46, 0.30, 0.95), mid=(0.80, 0.68, 1.0),
                                              hot=(1.0, 0.97, 1.0)), 3.4)
    return M


def marshal_body():
    B = Body(height=HEIGHT, shoulder=0.300, bulk=1.0, chest=1.0, limb=1.0, arm_out=0.42, arm_fwd=0.14,
             elbow_bend=0.30, stance=1.34)
    s = B.s
    B.torso = [(B.z(k), (rx * s, ry * s, yo * s)) for k, (rx, ry, yo) in TORSO]
    return B


# ===== 头骨、下颌、眼窝幽火 =====
SLANT = 0.42                     # 眼窝斜切：外侧高于内侧（怒目）


def shear_slant(obj, center, sd):
    """绕 center 把对象沿 x 做斜切：z += SLANT*sd*(x - cx)，让眼窝里的黑洞 / 光点跟着斜。"""
    c = Vector(center)
    m = Matrix(((1, 0, 0, 0), (0, 1, 0, 0), (SLANT * sd, 0, 1, 0), (0, 0, 0, 1)))
    transform(obj, Matrix.Translation(c) @ m @ Matrix.Translation(-c))
    return obj


def build_skull(ctx, B, M):
    s = B.s * HEAD_SCALE
    T = ctx.title
    hc = Vector((0, 0.020 * s, B.z(1.935)))
    rx, ry, rz = 0.076 * s, 0.104 * s, 0.112 * s
    ze, xe = hc.z - 0.016 * s, 0.036 * s
    zf = ze - 0.060 * s                                        # 颅底平面（上颌齿槽上缘）
    zfl = zf - hc.z

    def local(u, v):
        a, phi = u * TAU, v * math.pi
        sx, cz = math.sin(phi), math.cos(phi)
        front = max(0.0, math.cos(a))
        low = smoothstep(0.10, -0.85, cz)                       # 下脸：向前收窄、前突、拉长
        x = rx * sx * math.sin(a) * (1 - 0.30 * low * front ** 0.5)
        y = ry * sx * math.cos(a)
        z = rz * cz
        y += 0.020 * s * low * front ** 2 * math.exp(-(x / (0.050 * s)) ** 2)
        z += 0.016 * s * low * (1 - front) ** 2                 # 枕下收紧
        k = 0.006 * s                                           # 柔和压平：椭球底部切成平整的颅底面
        z = zfl + 0.5 * ((z - zfl) + math.sqrt((z - zfl) ** 2 + k * k))
        return Vector((x, y, z)), front

    def sp(u, v):
        p, front = local(u, v)
        d = p.normalized() if p.length > 1e-9 else Vector((0, 0, 1))
        x, wz = p.x, hc.z + p.z
        ax = abs(x)
        disp = 0.0
        for sd in (-1, 1):                                     # 眼窝：斜切的方圆深坑
            ox = (x - sd * xe) * sd
            lx = ox / (0.031 * s)
            lz = (wz - ze - SLANT * ox) / (0.027 * s)
            disp -= 0.062 * s * math.exp(-(lx * lx + lz * lz) ** 3) * front ** 1.3
        zb = ze + 0.030 * s + SLANT * (ax - xe)                # 眉弓：随眼窝上缘斜向外上，中间 V 形压低
        disp += 0.020 * s * math.exp(-((wz - zb) / (0.009 * s)) ** 2) * front ** 2 * \
            (1 - smoothstep(0.055 * s, 0.085 * s, ax))
        disp += 0.022 * s * math.exp(-((ax - 0.064 * s) / (0.017 * s)) ** 2
                                     - ((wz - ze + 0.040 * s) / (0.013 * s)) ** 2) * front   # 颧骨
        disp -= 0.014 * s * math.exp(-((ax - 0.050 * s) / (0.016 * s)) ** 2
                                     - ((wz - ze + 0.074 * s) / (0.014 * s)) ** 2) * front   # 颧下凹
        tn = (ze - 0.016 * s - wz) / (0.034 * s)                # 鼻腔：倒心形
        if 0 < tn < 1.2:
            wn = (0.007 + 0.012 * math.sin(min(1.0, tn) * math.pi * 0.78)) * s
            disp -= 0.034 * s * math.exp(-(x / wn) ** 4) * smoothstep(0, 0.12, tn) * \
                (1 - smoothstep(0.92, 1.15, tn)) * front ** 3
        disp -= 0.008 * s * math.exp(-((ax - 0.075 * s) / (0.015 * s)) ** 2
                                     - ((wz - ze - 0.01 * s) / (0.02 * s)) ** 2)   # 太阳穴
        return hc + p + d * disp
    skull = surface(f"{T} skull", sp, 76, 50, [M["bone"]], closed_u=True,
                    uvfn=lambda u, v: (u * 2, (1 - v) * 1.2))
    orient(skull, lambda c: hc)
    ctx.part(skull, rigid("Head"))
    proj = projector(skull, (0, -1, 0))
    eyes = {}
    for sd, label in SIDES:
        hit = proj(Vector((sd * xe, 1.0, ze)), 0.0)
        eyes[label] = hit + Vector((0, 0.008 * s, 0.0))
        void = ellipsoid(f"{T} socket void {label}", hit + Vector((0, 0.002 * s, 0)),
                         (0.028 * s, 0.013 * s, 0.025 * s), [M["void"]], 16, 10)
        ctx.part(shear_slant(void, hit, sd), rigid("Head"))
        eye = gem(f"{T} eye {label}", eyes[label], 0.0085 * s, M["glow"], (1.0, 0.6, 1.0))
        ctx.part(shear_slant(eye, eyes[label], sd), rigid(f"Eye.{label}"))
        # 眼窝里的幽火：一束外焰 + 一束内焰，向上向外飘出，盖过眉骨
        base = eyes[label] + Vector((0, 0.004 * s, 0.002 * s))
        ctx.part(flame_sheets(f"{T} eye flame {label}", base, (sd * 0.34, 0.42, 1.0), 0.24 * s, 0.050 * s,
                              [M["flame"]], n=4, seed=1.0 + sd, nv=14), rigid(f"Eye.{label}"))
        ctx.part(flame_sheets(f"{T} eye flame core {label}", base + Vector((0, 0.003 * s, 0)), (sd * 0.22, 0.38, 1.0),
                              0.15 * s, 0.028 * s, [M["flamehot"]], n=3, seed=3.0 + sd), rigid(f"Eye.{label}"))
    nose = proj(Vector((0, 1.0, ze - 0.036 * s)), 0.0)
    ctx.part(ellipsoid(f"{T} nasal void", nose + Vector((0, -0.001 * s, 0.002 * s)),
                       (0.013 * s, 0.009 * s, 0.020 * s), [M["void"]], 12, 8), rigid("Head"))
    # 颧弓：从眼窝下缘向外后方弓出的锐利骨梁
    for sd, label in SIDES:
        phi_c = math.acos(max(-1.0, min(1.0, (ze - 0.040 * s - hc.z) / rz))) / math.pi
        ang = sd * 1.02
        a0 = sp((ang % TAU) / TAU, phi_c)                       # 直接取头骨曲面上的点（侧面最宽处射线会擦边落空）
        a0 = a0 + (a0 - hc).normalized() * 0.003 * s
        a2 = Vector((sd * (rx + 0.002 * s), hc.y - 0.012 * s, ze - 0.034 * s))
        a1 = a0.lerp(a2, 0.5) + Vector((sd * 0.006 * s, 0.0, -0.004 * s))
        ctx.part(tube(f"{T} zygomatic {label}", [a0, a1, a2], [0.0085 * s, 0.0078 * s, 0.0065 * s], [M["bone"]], n=8,
                      fx=0.95, fy=0.80, up=(0, 0, 1), per=4), rigid("Head"))
        ctx.part(spike(f"{T} cheek spur {label}", a0 + Vector((0, 0.002 * s, -0.002 * s)),
                       a0 + Vector((sd * 0.010 * s, 0.014 * s, -0.020 * s)), 0.0075 * s, [M["bone"]], sides=5),
                 rigid("Head"))
    # 牙列与下颌：獠牙、重下颌
    vt = math.acos(max(-1.0, min(1.0, (zf + 0.008 * s - hc.z) / rz))) / math.pi
    teeth = []
    for i in range(10):
        a = lerp(-0.66, 0.66, i / 9)
        p = sp(a / TAU, vt)
        out = Vector((p.x, p.y - hc.y, 0)).normalized()
        teeth.append((Vector((p.x, p.y, zf - 0.004 * s)) - out * 0.006 * s, out))
    for i, (p, out) in enumerate(teeth):
        fang = i in (2, 7)
        if fang:
            ctx.part(spike(f"{T} fang up {i}", p + Vector((0, 0, 0.008 * s)), p + Vector((0, 0.004 * s, -0.030 * s)),
                           0.0078 * s, [M["bone"]], sides=6), rigid("Head"))
        else:
            ctx.part(ellipsoid(f"{T} tooth up {i}", p, (0.0074 * s, 0.0064 * s, 0.0112 * s), [M["bone"]], 8, 6),
                     rigid("Head"))
        low_p = p + Vector((0, -0.002 * s, -0.022 * s))
        if i in (1, 8):
            ctx.part(spike(f"{T} fang lo {i}", low_p + Vector((0, 0, -0.006 * s)), low_p + Vector((0, 0.004 * s, 0.026 * s)),
                           0.0072 * s, [M["bone"]], sides=6), rigid("Jaw"))
        else:
            ctx.part(ellipsoid(f"{T} tooth lo {i}", low_p, (0.0070 * s, 0.0060 * s, 0.0105 * s), [M["bone"]], 8, 6),
                     rigid("Jaw"))
    gonion = {"L": Vector((-0.062 * s, hc.y - 0.004 * s, ze - 0.106 * s)),
              "R": Vector((0.062 * s, hc.y - 0.004 * s, ze - 0.106 * s))}
    body_pts = [teeth[0][0] + Vector((-0.016 * s, -0.026 * s, -0.050 * s))]
    body_pts += [p + Vector((0, -0.010 * s, -0.050 * s)) - out * 0.002 * s for p, out in teeth[::3]]
    body_pts += [teeth[-1][0] + Vector((0.016 * s, -0.026 * s, -0.050 * s))]
    body_pts = [gonion["L"]] + body_pts + [gonion["R"]]
    nb = len(body_pts)
    rads = [(0.012 + 0.009 * math.exp(-((i - (nb - 1) / 2) / 1.6) ** 2)) * s for i in range(nb)]
    ctx.part(tube(f"{T} mandible", body_pts, rads, [M["bone"]], n=8, fx=1.40, fy=0.85, up=(0, 0, 1), per=4),
             rigid("Jaw"))
    chin = body_pts[nb // 2]
    ctx.part(spike(f"{T} chin spike", chin + Vector((0, 0.010 * s, 0.004 * s)),
                   chin + Vector((0, 0.020 * s, -0.036 * s)), 0.016 * s, [M["bone"]], sides=6, fx=1.1, fy=0.8),
             rigid("Jaw"))
    hinge = {}
    for sd, label in SIDES:
        hinge[label] = Vector((sd * (rx - 0.008 * s), hc.y - 0.016 * s, ze - 0.046 * s))
        ctx.part(tube(f"{T} ramus {label}", [gonion[label] + Vector((0, 0.004 * s, -0.006 * s)),
                                            gonion[label].lerp(hinge[label], 0.5) + Vector((sd * 0.002 * s, 0.004 * s, 0)),
                                            hinge[label]],
                      [0.013 * s, 0.012 * s, 0.009 * s], [M["bone"]], n=8, fx=1.5, fy=0.55, up=(0, 1, 0), per=3),
                 rigid("Jaw"))
        ctx.part(spike(f"{T} gonion spur {label}", gonion[label], gonion[label] + Vector((sd * 0.012 * s, -0.020 * s, -0.018 * s)),
                       0.010 * s, [M["bone"]], sides=6), rigid("Jaw"))
    jaw_hinge = (hinge["L"] + hinge["R"]) / 2
    return {"hc": hc, "ze": ze, "eyes": eyes, "jaw": (jaw_hinge, chin), "r": (rx, ry, rz)}


# ===== 王冠盔：拱冠 + 两层尖刺 + 眉甲 / 鼻梁甲 + 颊翼 + 后颈甲片 + 盔顶幽焰 =====
def build_helm(ctx, B, M, sk):
    s = B.s * HEAD_SCALE
    T = ctx.title
    hc, ze = sk["hc"], sk["ze"]
    rx, ry, rz = sk["r"]
    c = hc + Vector((0, -0.006 * s, 0.006 * s))
    rxh, ryh, rzh = rx + 0.013 * s, ry + 0.014 * s, rz + 0.018 * s
    brow_z, back_z = ze + 0.056 * s, hc.z - 0.066 * s

    def wrap(a):
        return (a + math.pi) % TAU - math.pi

    def rim_z(a):
        return lerp(brow_z, back_z, smoothstep(0.55, 2.3, abs(wrap(a))))

    def at_z(a, z, grow=0.0, floor=-1.0):
        cz = max(floor, min(1.0, (z - c.z) / rzh))
        sph = math.sqrt(max(0.0, 1 - cz * cz))
        return c + Vector(((rxh + grow) * sph * math.sin(a), (ryh + grow) * sph * math.cos(a), rzh * cz))

    def hp(u, v):
        a = u * TAU
        z = lerp(c.z + rzh * 0.999, rim_z(a), v ** 0.8)
        p = at_z(a, z)
        out = Vector((p.x - c.x, p.y - c.y, 0))
        out = out.normalized() if out.length > 1e-6 else Vector((0, 0, 0))
        flute = 0.0035 * s * max(0.0, math.cos(9 * a)) ** 6 * smoothstep(0.15, 0.6, v)
        flare = 0.005 * s * smoothstep(0.85, 1.0, v)
        return p + out * (flute + flare)
    helm = surface(f"{T} helm", hp, 64, 22, [M["haft"]], closed_u=True)
    orient(helm, lambda q: c)
    ctx.part(finish(helm, 0.007 * s, -1, 0), rigid("Head"))
    rim = [hp(i / 96, 1.0) + Vector((0, 0, -0.002 * s)) for i in range(96)]
    ctx.part(trim(f"{T} helm rim", rim, 0.0046 * s, M["trim"], closed=True), rigid("Head"))
    ctx.part(trim(f"{T} helm ridge", [hp(0.0, v) + (hp(0.0, v) - c).normalized() * 0.004 * s
                                     for v in [1 - i / 20 for i in range(21)]] +
                  [hp(0.5, v) + (hp(0.5, v) - c).normalized() * 0.004 * s for v in [i / 20 for i in range(1, 19)]],
                  0.0042 * s, M["trim"]), rigid("Head"))
    # 王冠圈：暗金宽带 + 上下滚边
    z0, z1 = brow_z + 0.003 * s, brow_z + 0.040 * s

    def band(u, v):
        a = u * TAU
        return at_z(a, lerp(z1, z0, v), 0.006 * s + 0.004 * s * v)
    crown = surface(f"{T} crown band", band, 84, 4, [M["gold"]], closed_u=True, uvfn=lambda u, v: (u * 6, v * 0.5))
    orient(crown, lambda q: Vector((c.x, c.y, q.z)))
    ctx.part(finish(crown, 0.006 * s, -1, 0), rigid("Head"))
    for z, g in ((z0, 0.011), (z1, 0.007)):
        ctx.part(trim(f"{T} crown rim {z:.2f}", [at_z(i / 90 * TAU, z, g * s) for i in range(90)],
                      0.0040 * s, M["trim"], closed=True), rigid("Head"))
    # 冠圈上的符文宝石排（嵌在带面中线）
    for k in range(12):
        a = (k + 0.5) / 12 * TAU
        if abs(wrap(a)) < 0.20:
            continue
        ctx.part(gem(f"{T} crown stud {k}", at_z(a, (z0 + z1) / 2, 0.0112 * s), 0.0050 * s, M["inlay"], (1, 0.5, 1)),
                 rigid("Head"))
    # 第二层冠环 + 两道交叉拱（御冠），拱顶一颗幽焰宝珠
    ring_z = c.z + rzh * 0.60
    ctx.part(trim(f"{T} circlet", [at_z(i / 80 * TAU, ring_z, 0.011 * s) for i in range(80)], 0.0036 * s, M["trim"],
                  closed=True), rigid("Head"))
    th0 = math.asin(max(-1.0, min(1.0, (z1 - c.z) / rzh)))
    for k in range(2):
        pts = []
        for i in range(25):
            th = lerp(th0, math.pi - th0, i / 24)
            h = (rxh if k == 0 else ryh) + 0.012 * s
            horiz = math.cos(th) * h
            pts.append(c + Vector((horiz * (1 if k == 0 else 0), horiz * (0 if k == 0 else 1), (rzh + 0.012 * s) * math.sin(th))))
        ctx.part(tube(f"{T} crown arch {k}", pts, [0.0058 * s] * len(pts), [M["gold"]], n=8, per=1), rigid("Head"))
        ctx.part(trim(f"{T} crown arch rib {k}", [p + Vector((0, 0, 0.006 * s)) for p in pts[2:-2]], 0.0026 * s, M["inlay"],
                      per=1), rigid("Head"))
    apex = c + Vector((0, 0, rzh + 0.018 * s))
    ctx.part(gem(f"{T} crown orb", apex + Vector((0, 0, 0.010 * s)), 0.016 * s, M["glow"], (1, 1, 1)), rigid("Plume"))
    ctx.part(tube(f"{T} crown orb seat", [apex - Vector((0, 0, 0.012 * s)), apex + Vector((0, 0, 0.004 * s))],
                  [0.016 * s, 0.011 * s], [M["gold"]], n=10, per=1), rigid("Head"))
    # 冠圈尖刺：12 根，大—小—中—小的节奏，正面最高，背面次高，各带底座环与宝石
    heights = {0: 0.27, 1: 0.12, 2: 0.19, 3: 0.10, 4: 0.16, 5: 0.09, 6: 0.22}
    tips = []
    for k in range(12):
        a = k / 12 * TAU
        kk = min(k, 12 - k)
        base = at_z(a, z1 - 0.004 * s, 0.009 * s)
        out = Vector((math.sin(a), math.cos(a), 0))
        d = (out * (0.22 + 0.10 * (kk == 6)) + Vector((0, 0, 1))).normalized()
        h = heights[kk] * s
        r = (0.020 if kk == 0 else (0.016 if kk % 2 == 0 else 0.011)) * s
        ctx.part(spike(f"{T} crown spire {k}", base - d * 0.014 * s, base + d * h, r, [M["gold"]], sides=4, fx=0.50,
                       fy=1.0, up=tuple(out)), rigid("Head"))
        ctx.part(trim(f"{T} spire ring {k}", ring_points(base + d * 0.012 * s, d, r * 1.25, 12), 0.0030 * s, M["trim"],
                      closed=True), rigid("Head"))
        tips.append(base + d * h)
        if kk % 2 == 0:
            ctx.part(gem(f"{T} crown gem {k}", base + out * 0.007 * s + Vector((0, 0, -0.016 * s)),
                         (0.010 if kk == 0 else 0.0072) * s, M["glow"], (1, 0.6, 1.3)), rigid("Head"))
    # 眉甲：正面一块 V 形尖甲，尖端下探到鼻梁，两侧带小刺
    front = at_z(0.0, brow_z + 0.012 * s, 0.013 * s)
    brow = [(-0.064 * s, 0.022 * s), (0.064 * s, 0.022 * s), (0.066 * s, 0.002 * s), (0.036 * s, -0.003 * s),
            (0.010 * s, -0.020 * s), (0.0, -0.058 * s), (-0.010 * s, -0.020 * s), (-0.036 * s, -0.003 * s),
            (-0.066 * s, 0.002 * s)]
    ctx.part(plate(f"{T} brow guard", [(x, -dz) for x, dz in brow], 0.010 * s, [M["gold"]], origin=front,
                   xaxis=(1, 0, 0), yaxis=(0, 0, -1), bulge=lambda x, y: -x * x / (0.20 * s) + 0.004 * s * (1 - abs(x) / (0.066 * s)),
                   bev=0.0024 * s), rigid("Head"))
    ctx.part(trim(f"{T} brow guard inlay", [front + Vector((x * s, 0.010 * s - x * x * s / 0.20, -dz * s))
                                          for x, dz in ((-0.052, 0.002), (-0.026, -0.004), (0.0, -0.040), (0.026, -0.004),
                                                        (0.052, 0.002))], 0.0022 * s, M["inlay"], per=3), rigid("Head"))
    # 颊翼：两侧向后下方掠出的尖翼（盖住颧弓上方的太阳穴）
    for sd, label in SIDES:
        def wing(u, v, sd=sd):
            a = sd * lerp(1.00, 2.15, u)
            zt = z0 + 0.002 * s
            depth = 0.020 * s + 0.092 * s * math.sin(math.pi * min(1.0, u * 0.85 + 0.05)) ** 1.1
            return at_z(a, zt - depth * v, 0.012 * s + 0.010 * s * v, floor=-0.62)
        w = surface(f"{T} cheek wing {label}", wing, 24, 8, [M["gold"]], uvfn=lambda u, v: (u * 2, v))
        orient(w, lambda q: c)
        ctx.part(finish(w, 0.005 * s, 1, 0), rigid("Head"))
        ctx.part(trim(f"{T} cheek wing edge {label}", [wing(i / 24, 1.0) + Vector((0, 0, -0.002 * s)) for i in range(25)],
                      0.0030 * s, M["trim"]), rigid("Head"))
        tip = wing(0.5, 1.0)
        ctx.part(spike(f"{T} cheek wing spike {label}", tip, tip + Vector((sd * 0.018 * s, -0.050 * s, -0.052 * s)),
                       0.010 * s, [M["gold"]], sides=4), rigid("Head"))
    # 后颈甲片：三层扇形下垂
    for k in range(3):
        zt = back_z + 0.020 * s - k * 0.040 * s

        def lame(u, v, zt=zt, k=k):
            a = math.pi + lerp(-1.05, 1.05, u) * (1 + 0.10 * k)
            z = zt - 0.062 * s * v * (1 - 0.35 * abs(2 * u - 1) ** 1.5) - 0.012 * s * abs(2 * u - 1)
            return at_z(a, z, 0.010 * s + 0.010 * s * k + 0.014 * s * v, floor=-0.60)
        lm = surface(f"{T} nape lame {k}", lame, 22, 6, [M["gold"] if k % 2 == 0 else M["haft"]])
        orient(lm, lambda q: c)
        ctx.part(finish(lm, 0.004 * s, 1, 0), rigid("Head"))
        ctx.part(trim(f"{T} nape lame edge {k}", [lame(i / 22, 1.0) for i in range(23)], 0.0026 * s, M["trim"]),
                 rigid("Head"))
    # 盔顶幽焰（挂 Plume 骨，Enrage 时膨胀）：拱顶宝珠上方一簇淡紫火舌
    pb = apex + Vector((0, 0, 0.020 * s))
    ctx.part(flame_sheets(f"{T} plume", pb, (0, -0.22, 1), 0.30 * s, 0.062 * s, [M["flame"]], n=5, seed=0.7, nv=16),
             rigid("Plume"))
    ctx.part(flame_sheets(f"{T} plume core", pb, (0, -0.18, 1), 0.19 * s, 0.034 * s, [M["flamehot"]], n=3, seed=2.1),
             rigid("Plume"))
    return {"plume": pb, "crown_tips": tips}


# ===== 脊柱、肋笼、胸骨、锁骨、骨盆 =====
def spine_y(B, k):
    return interp([(1.08, -0.030), (1.25, -0.048), (1.40, -0.078), (1.55, -0.082), (1.66, -0.058), (1.78, -0.020)],
                  k) * B.s


def spine_bone(k):
    return "Pelvis" if k < 1.26 else ("Spine" if k < 1.47 else ("Chest" if k < 1.665 else "Neck"))


def build_spine(ctx, B, M):
    s = B.s
    ks = [1.12 + i * 0.034 for i in range(17)] + [1.70, 1.735, 1.768, 1.800, 1.832]
    for i, k in enumerate(ks):
        z, y = B.z(k), spine_y(B, k)
        big = interp([(1.1, 1.25), (1.3, 1.15), (1.45, 0.95), (1.66, 0.80), (1.75, 0.70)], k)
        c = Vector((0, y, z))
        spec = rigid(spine_bone(k))
        objs = [ellipsoid(f"{ctx.title} vertebra {i}", c, (0.031 * s * big, 0.027 * s * big, 0.0150 * s), [M["bone"]], 10, 6)]
        back = (0.050 if k < 1.66 else 0.028) * s * big
        objs.append(spike(f"{ctx.title} vertebra spine {i}", c + Vector((0, -0.012 * s, 0.003 * s)),
                          c + Vector((0, -0.012 * s - back, -0.018 * s)), 0.0105 * s * big, [M["bone"]], sides=5,
                          fx=1.4, fy=0.6, up=(0, 0, 1)))
        for sd in (-1, 1):
            objs.append(spike(f"{ctx.title} vertebra wing {i}{sd}", c + Vector((sd * 0.014 * s, -0.008 * s, 0)),
                              c + Vector((sd * 0.048 * s * big, -0.020 * s, 0.004 * s)), 0.0080 * s * big, [M["bone"]],
                              sides=5))
        for o in objs:
            ctx.part(o, spec)
        if i < len(ks) - 1:                                       # 椎间盘：淡紫能量
            k2 = (k + ks[i + 1]) / 2
            ctx.part(ellipsoid(f"{ctx.title} disc {i}", (0, spine_y(B, k2), B.z(k2)),
                               (0.024 * s * big, 0.020 * s * big, 0.0050 * s), [M["glow"]], 8, 4), rigid(spine_bone(k)))


def build_ribs(ctx, B, M):
    s = B.s
    for k in range(7):
        z0 = B.z(1.622 - k * 0.040)
        drop = (0.050 + 0.008 * k) * s
        true = k < 5
        a_end = (0.46 + 0.040 * k) if true else (0.92 if k == 5 else 1.22)   # 前方敞开，露出心核
        rise = (0.020 + 0.012 * k) * s
        for sd, label in SIDES:
            pts = []
            n = 22
            for i in range(n + 1):
                t = i / n
                a = lerp(math.pi - 0.15, a_end, t)
                fr = (math.pi - a) / math.pi
                z = z0 - drop * smoothstep(0.0, 0.78, fr)
                if true:
                    z += rise * smoothstep(0.74, 1.0, fr)
                p = B.torso_point(a, z, -0.006 * s)
                pts.append(Vector((sd * p.x, p.y, p.z)))
            r0 = (0.0128 - 0.0006 * k) * s
            rad = [r0 * lerp(0.8, 1.10, math.sin(math.pi * min(1, i / n * 1.2))) for i in range(n + 1)]
            rad[-1] = r0 * (0.62 if true else 0.28)
            ctx.part(tube(f"{ctx.title} rib {label}{k}", pts, rad, [M["bone"]], n=6, fx=1.30, fy=0.85, up=(0, 0, 1),
                          per=2), rigid("Chest" if k < 5 else "Spine"))
    # 胸骨柄：顶端一截暗金护板（下方肋笼敞开露出心核）
    top, bot = B.z(1.648), B.z(1.585)
    ptop = B.torso_point(0, top, 0.004 * s)
    pbot = B.torso_point(0, bot, 0.012 * s)
    ya = (pbot - ptop).normalized()
    L = (pbot - ptop).length
    outline = [(0.0, 0.0), (0.042 * s, -0.010 * s), (0.038 * s, -0.40 * L), (0.018 * s, -0.80 * L), (0.0, -1.15 * L)]
    outline = outline + [(-x, y) for x, y in reversed(outline[1:-1])]
    st = plate(f"{ctx.title} sternum", [(x, -y) for x, y in outline], 0.013 * s, [M["gold"]], origin=ptop,
               xaxis=(1, 0, 0), yaxis=tuple(ya), bulge=lambda x, y: 0.008 * s * (1 - (x / (0.04 * s)) ** 2),
               bev=0.003 * s)
    ctx.part(st, rigid("Chest"))
    nrm = Vector((1, 0, 0)).cross(ya).normalized()
    if nrm.y < 0:
        nrm = -nrm
    ctx.part(gem(f"{ctx.title} sternum gem", ptop + ya * L * 0.45 + nrm * 0.014 * s, 0.012 * s, M["glow"],
                 (1, 0.5, 1.2)), rigid("Chest"))
    # 锁骨
    for sd, label in SIDES:
        S = B.arms[label]["shoulder"]
        ctx.part(tube(f"{ctx.title} clavicle {label}", [ptop + Vector((sd * 0.02 * s, -0.004 * s, 0)),
                                                        Vector((sd * 0.10 * s, 0.080 * s, B.z(1.655))),
                                                        Vector((S.x * 0.9, 0.010 * s, S.z + 0.018 * s))],
                      [0.015 * s, 0.013 * s, 0.017 * s], [M["bone"]], n=8, per=4), rigid("Chest"))


def build_pelvis_bones(ctx, B, M):
    s = B.s
    for sd, label in SIDES:
        c = Vector((sd * 0.090 * s, -0.012 * s, B.z(1.135)))
        ctx.part(ellipsoid(f"{ctx.title} ilium {label}", c, (0.062 * s, 0.034 * s, 0.058 * s), [M["bone"]], 16, 10),
                 rigid("Pelvis"))
        ctx.part(spike(f"{ctx.title} ilium crest {label}", c + Vector((sd * 0.030 * s, -0.004 * s, 0.040 * s)),
                       c + Vector((sd * 0.070 * s, -0.020 * s, 0.100 * s)), 0.016 * s, [M["bone"]], sides=6,
                       bend=0.012 * s, up=(0, -1, 0)), rigid("Pelvis"))
    ctx.part(ellipsoid(f"{ctx.title} sacrum", (0, -0.056 * s, B.z(1.10)), (0.050 * s, 0.026 * s, 0.062 * s),
                       [M["bone"]], 14, 10), rigid("Pelvis"))


# ===== 服务器心核（肋笼内机柜） =====
def build_core(ctx, B, M):
    """多层机架：顶部“心脏模块”（大发光透镜 + 双圈 + 辐条）+ 四个抽屉（各一种淡紫指示灯阵、金拉手、有的拉出半截），
    暗金外框与两侧发光导轨；线缆从肋骨之间垂出，尾端带金接头；两条导能管沿腰椎下行。"""
    s = B.s
    T = ctx.title
    cz = B.z(1.4515)
    w, d, y0 = 0.172 * s, 0.100 * s, 0.020 * s
    h = 0.282 * s
    top, bottom = cz + h / 2, cz - h / 2
    F = y0 + d / 2                                              # 机架前沿
    ctx.part(box(f"{T} core chassis", (0, y0, cz), (w + 0.018 * s, d, h + 0.012 * s), [M["haft"]]), rigid("Chest"))
    # 抽屉：前面板略凸出机壳，1、3 号拉出半截
    hd, pitch = 0.040 * s, 0.048 * s
    z_first = top - 0.080 * s - 0.008 * s - hd / 2
    for i in range(4):
        zc = z_first - i * pitch
        pull = (0.016 * s if i in (1, 3) else 0.0)
        Fd = F + 0.004 * s + pull
        dd = 0.55 * d + pull
        ctx.part(drawer(f"{T} core drawer {i}", (0, Fd - dd / 2, zc), (w - 0.008 * s, dd, hd),
                        [M["core"]], i / 4, (i + 1) / 4, flip=bool(i % 2)), rigid("Chest"))
        for sx in (-1, 1):
            ctx.part(tube(f"{T} core handle {i}{sx}",
                          [Vector((sx * (w / 2 - 0.040 * s), Fd, zc)), Vector((sx * (w / 2 - 0.040 * s), Fd + 0.012 * s, zc)),
                           Vector((sx * (w / 2 - 0.018 * s), Fd + 0.012 * s, zc)), Vector((sx * (w / 2 - 0.018 * s), Fd, zc))],
                          [0.0040 * s] * 4, [M["trim"]], n=6, per=2), rigid("Chest"))
        ctx.part(box(f"{T} core lip {i}", (0, Fd, zc + hd / 2 + 0.003 * s), (w - 0.004 * s, 0.006 * s, 0.003 * s),
                     [M["trim"]]), rigid("Chest"))
    # 心脏模块：深色壳 + 三层金圈 + 辐条 + 透镜
    zh = top - 0.040 * s
    Fh = F + 0.002 * s
    ctx.part(box(f"{T} core heart bay", (0, Fh - 0.275 * d, zh), (w - 0.008 * s, 0.55 * d, 0.076 * s), [M["haft"]]),
             rigid("Chest"))
    lens = Vector((0, Fh + 0.010 * s, zh))
    ctx.part(ellipsoid(f"{T} core heart", lens, (0.030 * s, 0.016 * s, 0.030 * s), [M["heart"]], 16, 10), rigid("CoreGlow"))
    ctx.part(ellipsoid(f"{T} core heart halo", lens + Vector((0, 0.006 * s, 0)), (0.046 * s, 0.010 * s, 0.046 * s),
                       [M["flame"]], 20, 8), rigid("CoreGlow"))
    for k, (r, mat, rad) in enumerate(((0.037, M["trim"], 0.0040), (0.050, M["inlay"], 0.0030), (0.060, M["trim"], 0.0034))):
        ctx.part(trim(f"{T} core bezel {k}", ring_points(lens + Vector((0, 0.002 * s, 0)), (0, 1, 0), r * s, 36),
                      rad * s, mat, closed=True, per=1), rigid("Chest"))
    for i in range(12):
        a = i / 12 * TAU
        dirv = Vector((math.cos(a), 0, math.sin(a)))
        ctx.part(tube(f"{T} core spoke {i}", [lens + dirv * 0.052 * s + Vector((0, 0.002 * s, 0)),
                                             lens + dirv * 0.060 * s + Vector((0, 0.002 * s, 0))],
                      [0.0032 * s] * 2, [M["inlay"]], n=5, per=1), rigid("Chest"))
    # 肋笼逆光：机架两侧、肋骨后方各一块发光背板，让肋骨剪影浮在淡紫光里（“心核发光强于周边”）
    for sx in (-1, 1):
        ctx.part(box(f"{T} core backlight {sx}", (sx * 0.150 * s, y0 - 0.020 * s, cz), (0.092 * s, 0.006 * s, h * 0.92), [M["backlight"]]),
                 rigid("Chest"))
    # 外框：金色立柱 + 顶底帽 + 发光导轨
    for sx in (-1, 1):
        ctx.part(box(f"{T} core post {sx}", (sx * (w / 2 + 0.004 * s), F, cz), (0.010 * s, 0.014 * s, h + 0.010 * s),
                     [M["gold"]]), rigid("Chest"))
        ctx.part(box(f"{T} core rail {sx}", (sx * (w / 2 - 0.0035 * s), F + 0.004 * s, cz), (0.0042 * s, 0.003 * s, h * 0.90),
                     [M["glow"]]), rigid("Chest"))
    for sz in (-1, 1):
        ctx.part(box(f"{T} core cap {sz}", (0, y0 - 0.002 * s, cz + sz * (h / 2 + 0.006 * s)),
                     (w + 0.030 * s, d + 0.014 * s, 0.014 * s), [M["gold"]]), rigid("Chest"))
    # 线缆：机架背面连到脊柱；机架下沿垂出的 6 根带金接头的线缆（从肋骨间穿出）；两条导能管沿腰椎下行
    def spine_w(p):
        return {"Chest": 1.0} if p.z > B.z(1.45) else ({"Spine": 1.0} if p.z > B.z(1.26) else {"Pelvis": 1.0})
    for sd in (-1, 1):
        for j, (zt, kz) in enumerate(((0.38, 1.60), (-0.12, 1.44))):
            a = Vector((sd * w * 0.3, y0 - d / 2, cz + h * zt))
            b = Vector((sd * 0.014 * s, spine_y(B, kz) + 0.014 * s, B.z(kz)))
            ctx.part(tube(f"{T} core cable {sd}{j}", [a, a.lerp(b, 0.5) + Vector((sd * 0.02 * s, 0, -0.02 * s)), b],
                          [0.0078 * s] * 3, [M["haft"]], n=8, per=4), rigid("Chest"))
        pts = [Vector((sd * w * 0.32, y0, bottom - 0.010 * s)), Vector((sd * 0.034 * s, 0.0, B.z(1.36))),
               Vector((sd * 0.030 * s, spine_y(B, 1.28) + 0.028 * s, B.z(1.28))),
               Vector((sd * 0.044 * s, spine_y(B, 1.18) + 0.034 * s, B.z(1.18)))]
        ctx.part(tube(f"{T} conduit {sd}", pts, [0.0070 * s] * 4, [M["inlay"]], n=8, per=5), fn(spine_w))
    for i, x in enumerate((-0.066, -0.040, -0.014, 0.014, 0.040, 0.066)):
        sw = 1 if x > 0 else -1
        zb0 = bottom - 0.004 * s
        path = [Vector((x * s, y0 + 0.020 * s, zb0)), Vector((x * s * 1.15, y0 + 0.062 * s, zb0 - 0.040 * s)),
                Vector((x * s * 1.35, y0 + 0.074 * s, zb0 - 0.100 * s - 0.016 * s * (i % 2))),
                Vector((x * s * 1.45, y0 + 0.056 * s, zb0 - 0.160 * s - 0.024 * (i % 3) * s))]
        ctx.part(tube(f"{T} core drop cable {i}", path, [0.0072 * s] * 4, [M["haft"]], n=8, per=4), fn(spine_w))
        end = path[-1]
        ctx.part(tube(f"{T} core plug {i}", [end, end + Vector((0, 0.0, -0.030 * s))], [0.0095 * s, 0.0095 * s],
                      [M["gold"]], n=8, per=1), fn(spine_w))
        ctx.part(gem(f"{T} core plug tip {i}", end + Vector((0, 0, -0.034 * s)), 0.0075 * s, M["glow"], (1, 1, 1)),
                 fn(spine_w))
    return lens


def fn(f):
    return ("fn", f)


# ===== 盔甲：领甲、背甲、叠片胸甲、腰带、腹甲裙、髂翼、腿甲 =====
def gorget_b3(ctx, B, mat, trim_mat=None, layers=((1.645, 1.695, 0.090, 0.070), (1.685, 1.735, 0.072, 0.056))):
    """颈甲（复制自 kit.humanoid.gorget，去掉细分、网格减半，面数 9 千 → 1 千）。"""
    s = B.s
    for k, (z0, z1, r0, r1) in enumerate(layers):
        z0, z1 = B.z(z0), B.z(z1)

        def g(u, v, z0=z0, z1=z1, r0=r0 * s, r1=r1 * s):
            a = u * TAU
            z = lerp(z0, z1, v) - 0.018 * s * max(0.0, math.cos(a)) ** 4 * (1 - v)
            r = lerp(r0, r1, v)
            return Vector((r * math.sin(a), 0.004 * s + 0.006 * s * v + r * math.cos(a) * 0.92, z))
        obj = surface(f"{ctx.title} gorget {k}", g, 40, 5, [mat], closed_u=True)
        orient(obj, lambda c: Vector((0, 0, c.z)))
        ctx.part(finish(obj, 0.005 * s, 1, 0), invdist(["Chest", "Neck"]))
        if trim_mat:
            rim = [g(i / 40, 1.0) for i in range(40)]
            rim = [p + Vector((p.x, p.y - 0.004 * s, 0)).normalized() * 0.005 * s for p in rim]
            ctx.part(trim(f"{ctx.title} gorget {k} trim", rim, 0.0026 * s, trim_mat, closed=True),
                     invdist(["Chest", "Neck"]))


def build_armor(ctx, B, M):
    s = B.s
    T = ctx.title
    shell(ctx, B, f"{T} collar", lambda a: B.z(1.672),
          lambda a: B.z(1.598) + 0.034 * s * (abs(a) / 1.25) ** 1.4, 0.020 * s, M["gold"], rigid("Chest"),
          a0=-1.25, a1=1.25, nu=44, nv=8, sub=0, thick=0.009 * s, trims=(M["trim"], 0.0036 * s))
    shell(ctx, B, f"{T} backplate", B.z(1.655), lambda a: B.z(1.33) - 0.04 * s * math.cos((a - math.pi) * 1.2),
          0.022 * s, M["haft"], rigid("Chest"), a0=1.9, a1=TAU - 1.9, nu=40, nv=14, sub=0, thick=0.009 * s,
          trims=(M["trim"], 0.0036 * s))
    gorget_b3(ctx, B, M["gold"], M["trim"], layers=((1.640, 1.690, 0.098, 0.082), (1.682, 1.728, 0.080, 0.066)))
    # 脊背纹章条：背甲中线一列金片 + 淡紫嵌线
    for i in range(7):
        zc = 1.60 - i * 0.040
        p = B.torso_point(math.pi, B.z(zc), 0.032 * s)
        ctx.part(ellipsoid(f"{T} back stud {i}", p, (0.020 * s - 0.0014 * s * i, 0.010 * s, 0.014 * s), [M["gold"]], 12, 8),
                 rigid("Chest"))
        ctx.part(gem(f"{T} back stud gem {i}", p + Vector((0, -0.008 * s, 0)), 0.0060 * s, M["inlay"], (1, 0.5, 1)),
                 rigid("Chest"))
    # 胸前金链 + 徽章
    path = [Vector((-0.170 * s, 0.078 * s, B.z(1.650))), Vector((-0.090 * s, 0.128 * s, B.z(1.610))),
            Vector((0.0, 0.142 * s, B.z(1.595))), Vector((0.090 * s, 0.128 * s, B.z(1.610))),
            Vector((0.170 * s, 0.078 * s, B.z(1.650)))]
    ctx.part(chain_links(f"{T} chest chain", path, 0.026 * s, 0.0030 * s, [M["trim"]]), rigid("Chest"))
    med = Vector((0, 0.150 * s, B.z(1.588)))
    ctx.part(ellipsoid(f"{T} medallion", med, (0.024 * s, 0.007 * s, 0.026 * s), [M["gold"]], 18, 10), rigid("Chest"))
    ctx.part(gem(f"{T} medallion gem", med + Vector((0, 0.007 * s, 0)), 0.0105 * s, M["glow"], (1, 0.5, 1.2)),
             rigid("Chest"))
    for i in range(11):                                              # 领甲前缘一排下垂小尖刺，呼应王冠
        a = lerp(-1.12, 1.12, i / 10)
        zc = B.z(1.598) + 0.034 * s * (abs(a) / 1.25) ** 1.4
        p0 = B.torso_point(a, zc + 0.004 * s, 0.026 * s)
        out = Vector((math.sin(a), math.cos(a), 0)).normalized()
        big = 1.0 if i % 2 == 0 else 0.6
        ctx.part(spike(f"{T} collar spike {i}", p0, p0 + out * 0.012 * s + Vector((0, 0, -0.046 * s * big)), 0.0085 * s,
                       [M["gold"]], sides=4), rigid("Chest"))
    build_cuirass(ctx, B, M)
    # 肋笼底环 + 腰带
    shell(ctx, B, f"{T} rib ring", B.z(1.305), B.z(1.252), 0.036 * s, M["gold"], rigid("Spine"), nu=72, nv=4, sub=0,
          thick=0.008 * s, trims=(M["trim"], 0.0034 * s))
    for i in range(10):
        a = i / 10 * TAU + 0.31
        ctx.part(gem(f"{T} ring stud {i}", B.torso_point(a, B.z(1.278), 0.046 * s), 0.0072 * s, M["inlay"], (1, 0.6, 1)),
                 rigid("Spine"))
    shell(ctx, B, f"{T} belt", B.z(1.190), B.z(1.122), 0.026 * s, M["gold"], rigid("Pelvis"), nu=72, nv=4, sub=0,
          thick=0.008 * s, trims=(M["trim"], 0.0034 * s))
    buckle = B.torso_point(0, B.z(1.156), 0.040 * s)
    crest = [(0.0, 0.050 * s), (0.040 * s, 0.032 * s), (0.052 * s, 0.0), (0.034 * s, -0.036 * s), (0.0, -0.054 * s),
             (-0.034 * s, -0.036 * s), (-0.052 * s, 0.0), (-0.040 * s, 0.032 * s)]
    ctx.part(plate(f"{T} buckle", crest, 0.016 * s, [M["gold"]], origin=buckle, xaxis=(1, 0, 0), yaxis=(0, 0, 1),
                   bulge=lambda x, y: 0.010 * s * (1 - (x * x + y * y) / (0.055 * s) ** 2), bev=0.003 * s),
             rigid("Pelvis"))
    ctx.part(gem(f"{T} buckle gem", buckle + Vector((0, 0.018 * s, 0)), 0.016 * s, M["glow"], (1.1, 0.5, 1.0)),
             rigid("Pelvis"))
    ctx.part(trim(f"{T} buckle ring", ring_points(buckle + Vector((0, 0.014 * s, 0)), (0, 1, 0), 0.026 * s, 24),
                  0.0034 * s, M["trim"], closed=True, per=1), rigid("Pelvis"))
    build_skirt(ctx, B, M)
    build_leg_armor(ctx, B, M)


def build_cuirass(ctx, B, M):
    """肋笼外缘的叠片胸甲：两侧各 5 片只包住肋骨架外缘（前方留出窗口，肋骨与心核从正面看得见）；
    窗口边缘一条金色立梁，随片起落有铆钉宝石。"""
    s = B.s
    T = ctx.title
    spec = rigid("Chest")
    for side, label in SIDES:
        a0, a1 = (0.92, 2.40) if side > 0 else (-2.40, -0.92)
        for k in range(5):
            zt = 1.662 - 0.074 * k
            zb = zt - 0.100

            def zb_f(a, zb=zb):
                f = clamp01((abs(a) - 0.92) / 1.48)
                return B.z(zb) - 0.034 * s * (1 - f) ** 1.2          # 窗口一侧更低成尖，向后收平
            mat = M["plate"] if k % 2 == 0 else M["gold"]
            shell(ctx, B, f"{T} cuirass {label}{k}", B.z(zt), zb_f, (0.020 + 0.005 * k) * s, mat, spec, a0=a0, a1=a1,
                  nu=34, nv=6, sub=0, thick=0.010 * s, trims=(M["trim"], 0.0032 * s),
                  shape=lambda a, z, k=k: 0.006 * s * smoothstep(0.92, 1.4, abs(a)) * (1 + 0.4 * k))
            ctx.part(gem(f"{T} cuirass rivet {label}{k}", B.torso_point(side * 0.99, B.z(zt - 0.040), (0.036 + 0.005 * k) * s),
                         0.0075 * s, M["inlay"], (1, 0.6, 1)), spec)
        pts = [B.torso_point(side * 0.90, B.z(1.64 - i * 0.012), 0.050 * s) for i in range(30)]
        ctx.part(tube(f"{T} window bar {label}", pts, [0.0085 * s] * len(pts), [M["gold"]], n=6, per=1), spec)


def clamp01(x):
    return max(0.0, min(1.0, x))


def tri_wave(x):
    """周期 1 的三角波：0 → 1 → 0。"""
    f = x - math.floor(x)
    return 1 - abs(2 * f - 1)


def build_skirt(ctx, B, M):
    """腰部：后侧与两侧三层尖齿腹甲裙（下缘一圈尖牙，齿数逐层递减）+ 髂尖刺；前方留给垂旗与大腿叠甲。"""
    s = B.s
    T = ctx.title
    for k, (zt, zb, g, tabs) in enumerate(((1.135, 1.052, 0.042, 11), (1.078, 0.992, 0.056, 9), (1.020, 0.932, 0.072, 8))):
        shell(ctx, B, f"{T} fauld {k}", B.z(zt),
              lambda a, zb=zb, tabs=tabs: B.z(zb) - 0.050 * s * tri_wave((a - 0.85) / (TAU - 1.70) * tabs) ** 0.9,
              g * s, M["gold"] if k == 1 else M["plate"], rigid("Pelvis"), a0=0.85, a1=TAU - 0.85, nu=64, nv=4, sub=0,
              thick=0.009 * s, trims=(M["trim"], 0.0030 * s))
    for side, label in SIDES:
        p = B.torso_point(side * 1.00, B.z(1.17), 0.060 * s)
        ctx.part(spike(f"{T} hip spike {label}", p, p + Vector((side * 0.090 * s, -0.020 * s, 0.060 * s)), 0.024 * s,
                       [M["gold"]], sides=6, bend=0.014 * s, up=(0, 0, 1)), rigid("Pelvis"))
        ctx.part(trim(f"{T} hip spike ring {label}", ring_points(p + Vector((side * 0.012 * s, 0, 0.008 * s)),
                                                                 (side, -0.2, 0.5), 0.030 * s, 16), 0.0044 * s, M["trim"],
                      closed=True, per=1), rigid("Pelvis"))
        ctx.part(gem(f"{T} hip gem {label}", B.torso_point(side * 0.72, B.z(1.12), 0.040 * s), 0.012 * s, M["glow"],
                     (1, 0.6, 1.2)), rigid("Pelvis"))


def limb_lame(ctx, name, a, b, r0, r1, v0, v1, out, arc, mat, spec, tip=0.0, flare=0.0, thick=0.008, nu=20, nv=6,
              trim_mat=None, trim_r=0.003, roff=0.0):
    """沿肢体段 a→b 的弧形叠甲片，下缘中线下探成尖（tip 米）；半径随 a→b 线性渐变，roff 让下一片略缩进上一片之下。"""
    axis, o, w = limb_frame(a, b, out)
    L = (b - a).length

    def pt(u, v):
        th = (2 * u - 1) * arc
        tt = lerp(v0, v1 + tip / L * (1 - abs(2 * u - 1)) ** 1.1, v)
        r = lerp(r0, r1, tt) + roff + flare * smoothstep(0.6, 1.0, v)
        return a.lerp(b, tt) + (o * math.cos(th) + w * math.sin(th)) * r

    def on_axis(c):
        return a + (b - a) * clamp01((c - a).dot(b - a) / (b - a).length_squared)
    obj = surface(name, pt, nu, nv, [mat], uvfn=lambda u, v: (u * 2, v))
    orient(obj, on_axis)
    ctx.part(finish(obj, thick, 1, 0), spec)
    if trim_mat:
        for v in (1.0,):
            pts = [pt(i / (nu * 2), v) for i in range(nu * 2 + 1)]
            pts = [q + (q - on_axis(q)).normalized() * thick * 1.1 for q in pts]
            ctx.part(trim(f"{name} edge", pts, trim_r, trim_mat), spec)
    return pt


def build_leg_armor(ctx, B, M):
    s = B.s
    T = ctx.title
    for side, label in SIDES:
        L = B.legs[label]
        hip, knee, ankle = L["hip"], L["knee"], L["ankle"]
        # 大腿叠甲：4 片尖下缘弧甲，上片压下片，金 / 象牙相间
        for k, (v0, v1) in enumerate(((0.04, 0.34), (0.26, 0.56), (0.48, 0.78), (0.68, 0.96))):
            limb_lame(ctx, f"{T} cuisse lame {label}{k}", hip, knee, 0.104 * s, 0.088 * s, v0, v1,
                      Vector((side * 0.28, 1, 0)), 1.40, M["gold"] if k % 2 else M["plate"],
                      rigid((f"Thigh.{label}", 1.0)), tip=0.050 * s, thick=0.009 * s, trim_mat=M["trim"],
                      trim_r=0.0032 * s, roff=-0.007 * s * k)
        kpt = poleyn(ctx, B, side, label, M["gold"], M["trim"], M["glow"], size=0.098, wing=0.085)
        ctx.part(spike(f"{T} knee spike {label}", kpt + Vector((0, 0.060 * s, 0.004 * s)),
                       kpt + Vector((0, 0.150 * s, 0.020 * s)), 0.022 * s, [M["gold"]], sides=6),
                 rigid((f"Thigh.{label}", 0.5), (f"Shin.{label}", 0.5)))
        limb_plate(ctx, f"{T} greave {label}", knee, ankle, 0.090 * s, 0.070 * s, M["gold"],
                   rigid(f"Shin.{label}"), Vector((side * 0.25, 1, 0)), arc=1.40, v0=0.14, v1=0.92, bulge=0.012 * s,
                   ridge=0.012 * s, flare1=0.010 * s, thick=0.009 * s, trim_mat=M["trim"], trim_r=0.0032 * s, nu=20,
                   nv=9, sub=0)
        ctx.part(trim(f"{T} greave inlay {label}",
                      [knee.lerp(ankle, t) + Vector((side * 0.02 * B.s, (lerp(0.090, 0.070, t) + 0.024) * s, 0))
                       for t in [0.22 + i / 10 * 0.6 for i in range(11)]], 0.0028 * s, M["inlay"]), rigid(f"Shin.{label}"))
        build_boot(ctx, B, M, side, label)


def build_boot(ctx, B, M, side, label):
    """铁靴：kit 靴底（脚跟挂 Foot、趾尖挂 Toe）+ 脚背 4 片尖前缘叠甲 + 金趾尖刺 + 脚跟刺 + 发光嵌线。"""
    s = B.s
    T = ctx.title
    L = B.legs[label]
    ankle, ball, toe = L["ankle"], L["ball"], L["toe"]
    sabaton(ctx, B, side, label, M["haft"], M["trim"], width=0.096, height=0.100, lames=0, toe_mat=M["gold"])
    wA = 0.096 * s
    for k in range(4):
        t0, t1 = 0.06 + 0.21 * k, 0.06 + 0.21 * k + 0.30

        def pt(u, v, t0=t0, t1=t1, k=k):
            th = (2 * u - 1) * 1.42
            tt = lerp(t0, t1 + 0.10 * (1 - abs(2 * u - 1)) ** 1.1, v)
            c = ankle.lerp(ball, tt)
            wd = wA * (1.04 - 0.22 * tt) - 0.004 * s * k
            ht = 0.062 * s * (1 - 0.40 * tt) - 0.003 * s * k
            return Vector((c.x + math.sin(th) * wd, c.y, c.z + 0.012 * s + math.cos(th) * ht))
        lame = surface(f"{T} boot lame {label}{k}", pt, 20, 6, [M["gold"] if k % 2 else M["plate"]],
                       uvfn=lambda u, v: (u * 2, v))
        orient(lame, lambda c, a=ankle, b=ball: Vector((c.x, 0, 0)) * 0 + Vector((a.x, c.y, a.z - 0.02 * s)))
        ctx.part(finish(lame, 0.008 * s, 1, 0), rigid(f"Foot.{label}"))
        edge = [pt(i / 40, 1.0) for i in range(41)]
        ctx.part(trim(f"{T} boot lame edge {label}{k}", [q + Vector((0, 0.003 * s, 0.003 * s)) for q in edge], 0.0030 * s,
                      M["trim"]), rigid(f"Foot.{label}"))
    ctx.part(spike(f"{T} toe spike {label}", toe + Vector((0, -0.020 * s, 0.020 * s)), toe + Vector((0, 0.070 * s, 0.026 * s)),
                   0.026 * s, [M["gold"]], sides=6), rigid(f"Toe.{label}"))
    ctx.part(spike(f"{T} heel spur {label}", ankle + Vector((0, -0.060 * s, 0.020 * s)),
                   ankle + Vector((0, -0.150 * s, 0.070 * s)), 0.024 * s, [M["gold"]], sides=6, bend=0.010 * s, up=(0, 0, 1)),
             rigid(f"Foot.{label}"))
    ctx.part(trim(f"{T} boot inlay {label}", [ankle.lerp(ball, t) + Vector((0, 0.002 * s, 0.078 * s * (1 - 0.40 * t) + 0.012 * s))
                                              for t in [0.05 + i / 10 * 0.8 for i in range(11)]], 0.0028 * s, M["inlay"]),
             rigid(f"Foot.{label}"))


# ===== 重型肩甲：5 片叠壳 + 肩顶三根节奏尖刺 + 前面纹章 =====
def build_pauldrons(ctx, B, M):
    s = B.s
    T = ctx.title
    radius, spread, rise, tilt = 0.290, 1.48, 1.10, 0.30
    theta = ((0.04, 0.86), (0.60, 1.14), (0.96, 1.40), (1.26, 1.66), (1.56, 1.92))
    shrink = (1.0, 0.965, 0.93, 0.895, 0.86)
    for side, label in SIDES:
        shoulder = B.arms[label]["shoulder"] + Vector((0, 0.001, 0.02 * s))
        spec = rigid(("Chest", 0.35), (f"UpperArm.{label}", 0.65))

        def lp(k, u, t, side=side, shoulder=shoulder):
            th0, th1 = theta[k]
            rr = radius * s * shrink[k]
            phi = u * spread
            taper = 1 - abs(u) ** 2.6
            mid, half = (th0 + th1) / 2, (th1 - th0) / 2
            th = mid + (t - 0.5) * 2 * half * taper
            d = Vector((math.cos(phi) * math.sin(th) * side, math.sin(phi) * math.sin(th) * rise, math.cos(th)))
            p = shoulder + d * rr * (1 + 0.06 * (1 - abs(u)) + 0.07 * math.exp(-(u / 0.12) ** 2))
            return shoulder + Matrix.Rotation(side * tilt, 3, "Y") @ (p - shoulder)
        mats = (M["gold"], M["plate"], M["gold"], M["plate"], M["haft"])
        for k in range(5):
            lame = surface(f"{T} pauldron {label}{k}", lambda u, v, k=k: lp(k, 2 * u - 1, v), 38, 10, [mats[k]],
                           uvfn=lambda u, v: (u * 2, v))
            orient(lame, lambda c, sh=shoulder: sh)
            ctx.part(finish(lame, 0.012 * s, 0, 0), spec)
            edge = [lp(k, 2 * i / 52 - 1, 1.0) for i in range(53)]
            edge = [p + (p - shoulder).normalized() * 0.005 * s for p in edge]
            ctx.part(trim(f"{T} pauldron {label}{k} trim", edge, 0.0044 * s, M["trim"]), spec)
            if k >= 1:
                for j in range(3):
                    u = lerp(-0.45, 0.45, j / 2)
                    q = lp(k, u, 0.55)
                    ctx.part(ellipsoid(f"{T} pauldron rivet {label}{k}{j}", q + (q - shoulder).normalized() * 0.010 * s,
                                       (0.0075 * s,) * 3, [M["gold"]], 8, 6), spec)
        # 肩顶骨刺（暗金）：三根大小相间，向后上扇开，各带底座环
        for i, (u, L) in enumerate(((-0.62, 0.20), (-0.08, 0.31), (0.46, 0.22))):
            p = lp(0, u, 0.30)
            out = (p - shoulder).normalized()
            d = (out * 0.50 + Vector((side * 0.30, -0.42 + 0.30 * u, 1.0))).normalized()
            ctx.part(spike(f"{T} pauldron spire {label}{i}", p - out * 0.014 * s, p + d * L * s, 0.034 * s,
                           [M["gold"]], sides=6, bend=0.030 * s, up=(0, -1, 0.3)), spec)
            ctx.part(trim(f"{T} spire collar {label}{i}", ring_points(p + d * 0.020 * s, d, 0.040 * s, 18), 0.0050 * s,
                          M["trim"], closed=True, per=1), spec)
            ctx.part(trim(f"{T} spire collar b {label}{i}", ring_points(p + d * 0.060 * s, d, 0.032 * s, 18), 0.0040 * s,
                          M["trim"], closed=True, per=1), spec)
        # 纹章：第二片上的发光宝珠 + 金座圈
        q = lp(1, 0.05, 0.50)
        n = (q - shoulder).normalized()
        ctx.part(gem(f"{T} pauldron emblem {label}", q + n * 0.014 * s, 0.020 * s, M["glow"], (1, 0.6, 1.2)), spec)
        ctx.part(trim(f"{T} pauldron emblem ring {label}", ring_points(q + n * 0.008 * s, n, 0.032 * s, 24), 0.0050 * s,
                      M["trim"], closed=True, per=1), spec)
        ctx.part(trim(f"{T} pauldron emblem ring b {label}", ring_points(q + n * 0.004 * s, n, 0.046 * s, 28), 0.0036 * s,
                      M["inlay"], closed=True, per=1), spec)


# ===== 四肢骨骼与臂甲 =====
def bone_tube(name, a, b, radii, mat, n=10):
    pts = [a.lerp(b, t) for t in (0.0, 0.12, 0.5, 0.88, 1.0)]
    return tube(name, pts, radii, [mat], n=n, per=3)


def build_limbs(ctx, B, M):
    s = B.s
    T = ctx.title
    for side, label in SIDES:
        a = B.arms[label]
        S, E, W = a["shoulder"], a["elbow"], a["wrist"]
        # ---- 臂骨：粗壮骨干 + 骨节 ----
        ctx.part(bone_tube(f"{T} humerus {label}", S, E, [0.052 * s, 0.037 * s, 0.030 * s, 0.037 * s, 0.050 * s],
                           M["bone"], n=12), rigid(f"UpperArm.{label}"))
        ctx.part(ellipsoid(f"{T} humeral head {label}", S, (0.060 * s,) * 3, [M["bone"]], 16, 10),
                 rigid(f"UpperArm.{label}"))
        ctx.part(ellipsoid(f"{T} elbow knob {label}", E, (0.050 * s,) * 3, [M["bone"]], 14, 10),
                 rigid((f"UpperArm.{label}", 0.5), (f"Forearm.{label}", 0.5)))
        fdir = (W - E).normalized()
        o = fdir.cross(Vector((0, 1, 0))).normalized() * 0.021 * s
        for k, sg in enumerate((-1, 1)):
            ctx.part(bone_tube(f"{T} forearm bone {label}{k}", E + o * sg + fdir * 0.01 * s, W + o * sg * 0.8,
                               [0.027 * s, 0.020 * s, 0.017 * s, 0.020 * s, 0.026 * s], M["bone"], n=10),
                     rigid(f"Forearm.{label}"))
        ctx.part(ellipsoid(f"{T} wrist knob {label}", W, (0.036 * s,) * 3, [M["bone"]], 12, 8), rigid(f"Forearm.{label}"))
        # ---- 上臂甲：半包肱骨的叠甲 + 两道环 + 肘甲 ----
        limb_plate(ctx, f"{T} rerebrace {label}", S, E, 0.100 * s, 0.085 * s, M["plate"], rigid(f"UpperArm.{label}"),
                   Vector((side, 0.05, 0.6)), arc=1.80, v0=0.30, v1=0.90, bulge=0.008 * s, ridge=0.010 * s,
                   thick=0.010 * s, trim_mat=M["trim"], trim_r=0.0034 * s, nu=24, nv=9, sub=0)
        ax = (E - S).normalized()
        for t, rr in ((0.28, 0.088), (0.92, 0.080)):
            c = S.lerp(E, t)
            ctx.part(trim(f"{T} arm ring {label}{t}", ring_points(c, ax, rr * s, 24), 0.0070 * s, M["trim"], closed=True,
                          per=1), rigid(f"UpperArm.{label}"))
        ctx.part(trim(f"{T} rerebrace inlay {label}", [S.lerp(E, t) + Vector((side * (0.095 - 0.012 * t) * s, 0.012 * s, 0.03 * s))
                                                      for t in [0.36 + i / 10 * 0.50 for i in range(11)]],
                      0.0030 * s, M["inlay"]), rigid(f"UpperArm.{label}"))
        ctx.part(ellipsoid(f"{T} couter {label}", E + Vector((side * 0.018 * s, -0.026 * s, 0)),
                           (0.058 * s, 0.056 * s, 0.060 * s), [M["gold"]], 18, 12),
                 rigid((f"UpperArm.{label}", 0.5), (f"Forearm.{label}", 0.5)))
        ctx.part(spike(f"{T} elbow spur {label}", E + Vector((side * 0.014 * s, -0.050 * s, 0)),
                       E + Vector((side * 0.045 * s, -0.150 * s, 0.045 * s)), 0.024 * s, [M["gold"]], sides=6,
                       bend=0.014 * s, up=(0, 0, 1)), rigid(f"Forearm.{label}"))
        ctx.part(trim(f"{T} couter ring {label}", ring_points(E + Vector((side * 0.018 * s, -0.026 * s, 0)), (0, 1, 0), 0.050 * s, 22),
                      0.0040 * s, M["trim"], closed=True, per=1), rigid((f"UpperArm.{label}", 0.5), (f"Forearm.{label}", 0.5)))
        # ---- 前臂甲：整圈护臂 + 腕口喇叭 + 发光嵌线 ----
        limb_plate(ctx, f"{T} vambrace {label}", E, W, 0.070 * s, 0.082 * s, M["gold"], rigid(f"Forearm.{label}"),
                   Vector((side, -0.35, 0.25)), closed=True, v0=0.30, v1=0.97, flare1=0.006 * s, ridge=0.014 * s,
                   thick=0.009 * s, trim_mat=M["trim"], trim_r=0.0036 * s, nu=26, nv=9, sub=0)
        oo = Vector((side, -0.35, 0.25))
        oo = (oo - fdir * oo.dot(fdir)).normalized()
        ctx.part(trim(f"{T} vambrace inlay {label}",
                      [E.lerp(W, t) + oo * (lerp(0.070, 0.082, t) * s + 0.022 * s) for t in [0.42 + i / 10 * 0.52 for i in range(11)]],
                      0.0030 * s, M["inlay"]), rigid(f"Forearm.{label}"))
        # ---- 腿骨：粗股骨 / 胫骨 + 骨节 ----
        L = B.legs[label]
        hip, knee, ankle = L["hip"], L["knee"], L["ankle"]
        ctx.part(bone_tube(f"{T} femur {label}", hip, knee, [0.056 * s, 0.041 * s, 0.034 * s, 0.041 * s, 0.056 * s],
                           M["bone"], n=12), rigid(f"Thigh.{label}"))
        ctx.part(ellipsoid(f"{T} femoral head {label}", hip + Vector((-side * 0.012 * s, 0, 0.012 * s)),
                           (0.050 * s,) * 3, [M["bone"]], 14, 10), rigid(f"Thigh.{label}"))
        ctx.part(ellipsoid(f"{T} trochanter {label}", hip + Vector((side * 0.040 * s, -0.004 * s, -0.014 * s)),
                           (0.030 * s, 0.030 * s, 0.040 * s), [M["bone"]], 12, 8), rigid(f"Thigh.{label}"))
        ctx.part(ellipsoid(f"{T} knee knob {label}", knee + Vector((0, -0.010 * s, 0)), (0.056 * s, 0.050 * s, 0.050 * s),
                           [M["bone"]], 14, 10), rigid((f"Thigh.{label}", 0.5), (f"Shin.{label}", 0.5)))
        ctx.part(bone_tube(f"{T} tibia {label}", knee, ankle, [0.046 * s, 0.034 * s, 0.027 * s, 0.030 * s, 0.040 * s],
                           M["bone"], n=12), rigid(f"Shin.{label}"))
        ctx.part(bone_tube(f"{T} fibula {label}", knee + Vector((side * 0.030 * s, -0.016 * s, -0.02 * s)),
                           ankle + Vector((side * 0.026 * s, -0.014 * s, 0.01 * s)),
                           [0.014 * s, 0.011 * s, 0.009 * s, 0.010 * s, 0.013 * s], M["bone"], n=8), rigid(f"Shin.{label}"))
        ctx.part(ellipsoid(f"{T} ankle knob {label}", ankle, (0.040 * s, 0.040 * s, 0.040 * s), [M["bone"]], 12, 8),
                 rigid(f"Shin.{label}"))


# ===== 护手：手背金甲板 + 腕环 + 指节刺 =====
def build_gauntlets(ctx, B, M):
    s = B.s
    T = ctx.title
    sc = HAND_SC
    for side, label in SIDES:
        h = B.hands[label]
        f, n, sv = h["f"], h["n"], h["s"]
        W0 = h["wrist"]
        spec = rigid(f"Hand.{label}")
        base = W0 + f * 0.030 * s * sc - n * 0.034 * s * sc
        outline = [(-0.030 * s * sc, 0.0), (0.030 * s * sc, 0.0), (0.036 * s * sc, 0.050 * s * sc),
                   (0.032 * s * sc, 0.092 * s * sc), (0.0, 0.104 * s * sc), (-0.032 * s * sc, 0.092 * s * sc),
                   (-0.036 * s * sc, 0.050 * s * sc)]
        ctx.part(plate(f"{T} backhand {label}", outline, 0.010 * s, [M["gold"]], origin=base, xaxis=tuple(-sv), yaxis=tuple(f),
                       bulge=lambda x, y, sc=sc: 0.010 * s * (1 - (x / (0.036 * s * sc)) ** 2) * math.sin(math.pi * min(1.0, max(0.0, y / (0.104 * s * sc)))),
                       bev=0.0025 * s), spec)
        ctx.part(trim(f"{T} backhand ridge {label}", [base + f * (0.012 + 0.012 * i) * s * sc - n * 0.014 * s * sc
                                                      for i in range(8)], 0.0030 * s, M["inlay"], per=2), spec)
        ctx.part(gem(f"{T} backhand gem {label}", base + f * 0.052 * s * sc - n * 0.018 * s * sc, 0.0075 * s, M["glow"],
                     (1, 0.6, 1.2)), spec)
        for k, off in enumerate((-0.020, 0.0, 0.020)):
            q = base + f * 0.094 * s * sc + sv * off * s * sc - n * 0.012 * s * sc
            ctx.part(spike(f"{T} knuckle spike {label}{k}", q, q + f * 0.022 * s * sc - n * 0.014 * s * sc, 0.0075 * s, [M["gold"]],
                           sides=4), spec)
        ctx.part(trim(f"{T} wrist band {label}", ring_points(W0 + f * 0.004 * s * sc, f, 0.036 * s * sc, 18), 0.0060 * s,
                      M["trim"], closed=True, per=1), rigid((f"Forearm.{label}", 0.4), (f"Hand.{label}", 0.6)))


# ===== 旗枪（右手） =====
def pen_weights(c0, A, joints=(0.0, 0.40, 0.78, 1.20)):
    """旗布蒙皮：d 为到横杆的距离（沿 -A），三节骨 Pen1~3 的帐篷权重；贴近横杆处混入 Hand.R。"""
    mids = [(joints[i] + joints[i + 1]) / 2 for i in range(3)]
    span = [joints[i + 1] - joints[i] for i in range(3)]

    def w(p):
        d = (c0 - p).dot(A)
        out = {}
        for i in range(3):
            v = max(0.0, 1.0 - abs(d - mids[i]) / span[i])
            if i == 2 and d > mids[2]:
                v = 1.0
            if i == 0 and d < mids[0]:
                v = min(1.0, v + 0.0) if d > 0.0 else 1.0
            out[f"Pen{i + 1}"] = v
        tot = sum(out.values()) or 1.0
        out = {k: v / tot for k, v in out.items()}
        top = max(0.0, 1.0 - d / 0.10)
        if top > 0:
            out = {k: v * (1 - top) for k, v in out.items()}
            out["Hand.R"] = top
        return out
    return w


def build_spear(ctx, B, M):
    s = B.s
    h = B.hands["R"]
    f, n, A = h["f"], h["n"], h["s"]
    sc = HAND_SC
    G = h["wrist"] + f * 0.074 * s * sc + n * 0.030 * s * sc
    W = f.cross(A).normalized()            # 旗面方向：待机握姿下朝 +X 外侧
    N = A.cross(W).normalized()

    def P(t, w=0.0, nn=0.0):
        return G + A * t + W * w + N * nn
    spec = rigid("Hand.R")
    r = 0.052
    ctx.part(tube(f"{ctx.title} spear shaft", [P(-1.30), P(2.62)], [r, r * 0.92], [M["haft"]], n=12, per=1), spec)
    ctx.part(spike(f"{ctx.title} spear butt", P(-1.28), P(-1.52), r * 1.2, [M["gold"]], sides=8), spec)
    for t in (-1.24, -0.72, -0.20, 0.22, 0.80, 1.40, 2.00, 2.55):
        rr = r * (1.35 if t in (-1.24, 2.55) else 1.18)
        ctx.part(trim(f"{ctx.title} spear ring {t}", ring_points(P(t), A, rr, 20), 0.014, M["trim"], closed=True, per=1),
                 spec)
    for t in (-0.46, 1.10, 1.70):
        ctx.part(trim(f"{ctx.title} spear inlay {t}", ring_points(P(t), A, r * 1.05, 20), 0.007, M["inlay"],
                      closed=True, per=1), spec)
    # 枪头：暗金套筒 + 骨白叶刃（发光中脊）+ 两侧月牙
    ctx.part(tube(f"{ctx.title} spear socket", [P(2.58), P(2.66), P(2.80), P(2.88)], [0.070, 0.082, 0.064, 0.050],
                  [M["gold"]], n=12, per=2), spec)
    ctx.part(gem(f"{ctx.title} spear orb", P(2.74, 0, 0.0), 0.075, M["glow"], (1.0, 1.0, 1.0)), spec)
    L0, L1 = 2.86, 3.80
    blade = [(0.0, 0.0), (0.090, 0.05), (0.145, 0.20), (0.138, 0.44), (0.088, 0.68), (0.0, L1 - L0)]
    blade = blade + [(-x, y) for x, y in reversed(blade[1:-1])]
    ctx.part(plate(f"{ctx.title} spear blade", blade, 0.034, [M["plate"]], origin=P(L0), xaxis=tuple(N), yaxis=tuple(A),
                   bulge=lambda x, y: 0.016 * (1 - (x / 0.145) ** 2), bev=0.006), spec)
    for sd in (-1, 1):
        edge = [P(L0 + y, 0, sd * x) for x, y in ((0.09, 0.05), (0.147, 0.20), (0.140, 0.44), (0.090, 0.68), (0.0, L1 - L0))]
        ctx.part(trim(f"{ctx.title} spear edge {sd}", edge, 0.008, M["trim"], per=3), spec)
        ctx.part(spike(f"{ctx.title} spear crescent {sd}", P(2.80, 0, sd * 0.06), P(3.10, 0, sd * 0.30), 0.035,
                       [M["gold"]], sides=6, bend=0.10, up=tuple(-A)), spec)
    ctx.part(trim(f"{ctx.title} spear fuller", [P(L0 + 0.08 + i * 0.05, 0.016, 0) for i in range(12)], 0.006,
                  M["inlay"], per=1), spec)
    ctx.part(trim(f"{ctx.title} spear fuller b", [P(L0 + 0.08 + i * 0.05, -0.016, 0) for i in range(12)], 0.006,
                  M["inlay"], per=1), spec)
    # 横杆 + 燕尾旗（Pen1~3 三节骨链，挂 Hand.R，绕横杆轴摆；旗布 / 滚边 / 宝珠按到横杆的距离蒙皮）
    tb = 2.50
    ctx.part(tube(f"{ctx.title} spear crossbar", [P(tb, -0.04), P(tb, 1.02)], [0.026, 0.022], [M["trim"]], n=8, per=1), spec)
    ctx.part(gem(f"{ctx.title} crossbar gem", P(tb, 1.04), 0.04, M["glow"], (1, 1, 1)), spec)
    ctx.part(spike(f"{ctx.title} crossbar thorn", P(tb, 1.06), P(tb, 1.22), 0.022, [M["gold"]], sides=4), spec)
    pen_w, pen_len, notch = 0.92, 1.15, 0.34
    c0 = P(tb - 0.03, 0.06 + pen_w / 2, 0.0)

    def pen_pt(u, v):
        down = v * (pen_len - notch * (1 - abs(2 * u - 1)) ** 0.9)
        wave = 0.05 * math.sin(u * 5.5 + v * 2.0) * smoothstep(0.05, 0.3, u)
        return P(tb - 0.03 - down, 0.06 + u * pen_w, wave)
    pen = surface(f"{ctx.title} spear pennant", pen_pt, 14, 22, [M["banner"]], uvfn=lambda u, v: (u, 1 - v * 0.9))
    orient(pen, lambda c: c - N)
    solidify(pen, 0.016, 0)
    spec_pen = fn(pen_weights(c0, A))
    ctx.part(apply_all(pen), spec_pen)
    for u in (0.0, 1.0):
        ctx.part(trim(f"{ctx.title} pennant edge {u}", [pen_pt(u, j / 18) + N * 0.006 for j in range(19)], 0.009, M["trim"],
                      per=2), spec_pen)
        ctx.part(gem(f"{ctx.title} pennant tip {u}", pen_pt(u, 1.0) + N * 0.01, 0.032, M["glow"], (0.8, 0.8, 1.2)), spec_pen)
    ctx.part(trim(f"{ctx.title} pennant hem", [pen_pt(i / 24, 1.0) + N * 0.006 for i in range(25)], 0.010, M["hem"], per=2),
             spec_pen)
    ctx.part(trim(f"{ctx.title} pennant top", [pen_pt(i / 14, 0.0) + N * 0.006 for i in range(15)], 0.010, M["trim"], per=2),
             spec_pen)
    return {"G": G, "A": A, "W": W, "off": G - h["wrist"], "pen": (c0, pen_len)}


# ===== 军旗架 + 三面燕尾军旗 =====
def poles_def():
    """(底座, 顶端, 旗宽, 旗长, 燕尾深) —— 中旗最高，两侧外倾 22° 成扇形。"""
    out = []
    base_c = Vector((0.0, -0.64, 4.18))
    out.append((base_c, base_c + Vector((0, 0, 2.62)), 1.00, 1.62, 0.30))
    for sd in (-1, 1):
        b = Vector((sd * 0.34, -0.62, 4.12))
        ang = math.radians(22)
        out.append((b, b + Vector((sd * math.sin(ang), 0, math.cos(ang))) * 2.20, 0.84, 1.38, 0.26))
    return out


def build_banners(ctx, B, M):
    s = B.s
    T = ctx.title
    banners = []
    for k, (b, t, w, L, notch) in enumerate(poles_def()):
        bone = f"Pole{k}"
        spec = rigid(bone)
        ax = (t - b).normalized()
        ctx.part(tube(f"{T} pole {k}", [b - ax * 0.12, t], [0.050, 0.043], [M["haft"]], n=10, per=1), spec)
        for q in (0.12, 0.45, 0.75):
            ctx.part(trim(f"{T} pole ring {k}{q}", ring_points(b.lerp(t, q), ax, 0.056, 16), 0.013, M["trim"],
                          closed=True, per=1), spec)
        # 顶饰：套筒 + 微型王冠笼（五根弧形冠肋合拢于顶尖，环上五根短刺，节奏同头盔）+ 宝珠 + 幽火（挂 Wisp 骨）
        ctx.part(tube(f"{T} finial socket {k}", [t - ax * 0.04, t + ax * 0.12], [0.064, 0.054], [M["gold"]], n=12, per=1), spec)
        u = ax.orthogonal().normalized()
        v = ax.cross(u)
        ring_c = t + ax * 0.12
        ctx.part(trim(f"{T} finial ring {k}", ring_points(ring_c, ax, 0.078, 20), 0.014, M["trim"], closed=True, per=1), spec)
        apex = t + ax * 0.50
        for j in range(5):
            a = j / 5 * TAU
            d = u * math.cos(a) + v * math.sin(a)
            ctx.part(tube(f"{T} finial rib {k}{j}", [ring_c + d * 0.078, t + ax * 0.26 + d * 0.092, apex - ax * 0.02 + d * 0.010],
                          [0.016, 0.012, 0.008], [M["gold"]], n=6, per=4), spec)
            a2 = a + math.pi / 5
            d2 = u * math.cos(a2) + v * math.sin(a2)
            ctx.part(spike(f"{T} finial thorn {k}{j}", ring_c + d2 * 0.076, ring_c + d2 * 0.130 + ax * (0.14 if j % 2 == 0 else 0.09),
                           0.016, [M["gold"]], sides=4), spec)
        ctx.part(spike(f"{T} finial tip {k}", apex - ax * 0.02, apex + ax * 0.14, 0.020, [M["gold"]], sides=4), spec)
        orb = t + ax * 0.30
        ctx.part(gem(f"{T} finial orb {k}", orb, 0.050, M["glow"], (1, 1, 1)), rigid(f"Wisp{k}"))
        ctx.part(flame_sheets(f"{T} finial wisp {k}", orb, (0, -0.2, 1), 0.54, 0.085, [M["flame"]], n=3, seed=k),
                 rigid(f"Wisp{k}"))
        ctx.part(flame_sheets(f"{T} finial wisp core {k}", orb, (0, -0.15, 1), 0.32, 0.045, [M["flamehot"]], n=2,
                              seed=k + 4.0), rigid(f"Wisp{k}"))
        # 横杆与旗面
        tz = t.z - 0.22
        tq = (tz - b.z) / (t.z - b.z)
        cb = b.lerp(t, tq)
        ctx.part(tube(f"{T} crossbar {k}", [cb + Vector((-w / 2 - 0.06, 0, 0)), cb + Vector((w / 2 + 0.06, 0, 0))],
                      [0.028, 0.028], [M["trim"]], n=8, per=1), spec)
        for sd in (-1, 1):
            ctx.part(gem(f"{T} crossbar cap {k}{sd}", cb + Vector((sd * (w / 2 + 0.08), 0, 0)), 0.042, M["gold"],
                         (1, 1, 1)), spec)
            ctx.part(spike(f"{T} crossbar thorn {k}{sd}", cb + Vector((sd * (w / 2 + 0.10), 0, 0)),
                           cb + Vector((sd * (w / 2 + 0.24), 0, 0.03)), 0.022, [M["gold"]], sides=4), spec)
            ctx.part(tube(f"{T} tassel {k}{sd}", [cb + Vector((sd * (w / 2 + 0.08), 0, -0.03)),
                                                cb + Vector((sd * (w / 2 + 0.09), -0.01, -0.40))],
                          [0.012, 0.006], [M["trim"]], n=6, per=1), spec)
            ctx.part(gem(f"{T} tassel tip {k}{sd}", cb + Vector((sd * (w / 2 + 0.09), -0.01, -0.44)), 0.03,
                         M["hem"], (0.8, 0.8, 1.4)), spec)
        depth = -(cb.y - 0.075)
        g = Banner(f"Ban{k}_", bone, tz - 0.02, tz - 0.02 - L, [(0, w), (1, w * 0.96)], [(0, depth), (1, depth)],
                   side=-1, K=3, joints=(0, 0.25, 0.50, 0.75, 1.0), curve=0.10, point=0.0, cx=cb.x, flutter=0.035,
                   notch=notch)
        g.build(ctx, [M["banner"]], f"{T} banner {k}", nu=16, nv=26, thickness=0.018, edges=(M["trim"], 0.012))
        hem = [g.point(i / 30, 1.0) + Vector((0, -0.004, 0)) for i in range(31)]
        ctx.part(trim(f"{T} banner hem {k}", hem, 0.010, M["hem"]), garment(g))
        for uu in (0.0, 1.0):
            ctx.part(gem(f"{T} banner tip {k}{uu}", g.point(uu, 1.0) + Vector((0, 0, -0.02)), 0.028, M["glow"],
                         (0.8, 0.8, 1.3)), garment(g))
        banners.append(g)
    # 军旗架：横梁 + 三个套筒 + 背甲上的安装板 + 中桅 + 两根斜撑（中桅从披风背中撕缝里穿过）
    rack_z, rack_y = 4.13, -0.63
    ctx.part(tube(f"{T} rack beam", [Vector((-0.42, rack_y, rack_z)), Vector((0, rack_y - 0.02, rack_z + 0.03)),
                                     Vector((0.42, rack_y, rack_z))], [0.040, 0.050, 0.040], [M["gold"]], n=10, per=4),
             rigid("Chest"))
    for k, (b, t, *_rest) in enumerate(poles_def()):
        ax = (t - b).normalized()
        ctx.part(tube(f"{T} rack socket {k}", [b - ax * 0.16, b + ax * 0.16], [0.074, 0.068], [M["gold"]], n=12, per=1),
                 rigid("Chest"))
        ctx.part(trim(f"{T} rack socket ring {k}", ring_points(b + ax * 0.16, ax, 0.072, 18), 0.013, M["trim"], closed=True,
                      per=1), rigid("Chest"))
    mast = [Vector((0, -0.42, 3.56)), Vector((0, -0.52, 3.86)), Vector((0, -0.61, 4.10))]
    ctx.part(tube(f"{T} rack mast", mast, [0.062, 0.054, 0.052], [M["gold"]], n=12, per=4), rigid("Chest"))
    for q in (0.30, 0.62):
        c = mast[0].lerp(mast[2], q)
        ctx.part(trim(f"{T} rack mast ring {q}", ring_points(c, (mast[2] - mast[0]).normalized(), 0.066, 18), 0.012, M["trim"],
                      closed=True, per=1), rigid("Chest"))
    for sd in (-1, 1):
        ctx.part(tube(f"{T} rack strut {sd}", [Vector((0, -0.52, 3.88)), Vector((sd * 0.22, -0.59, 4.03)),
                                              Vector((sd * 0.38, -0.63, 4.11))], [0.030, 0.028, 0.034], [M["gold"]], n=8,
                      per=3), rigid("Chest"))
    mount = [(0.0, 0.26), (0.14, 0.18), (0.17, -0.02), (0.10, -0.20), (0.0, -0.28), (-0.10, -0.20), (-0.17, -0.02),
             (-0.14, 0.18)]
    ctx.part(plate(f"{T} rack mount", mount, 0.040, [M["gold"]], origin=(0, -0.435, 3.60), xaxis=(1, 0, 0), yaxis=(0, 0, 1),
                   bulge=lambda x, y: -0.025 * (1 - (x * x + y * y) / 0.06), bev=0.007), rigid("Chest"))
    ctx.part(gem(f"{T} rack mount gem", (0, -0.475, 3.60), 0.050, M["glow"], (1, 0.6, 1.2)), rigid("Chest"))
    ctx.part(trim(f"{T} rack mount ring", ring_points(Vector((0, -0.465, 3.60)), (0, -1, 0), 0.075, 22), 0.010, M["trim"],
                  closed=True, per=1), rigid("Chest"))
    return banners


# ===== 布料：幽灵斗篷、前垂旗 =====
def cloth(B):
    s = B.s
    base = lambda u: B.z(0.36) + 0.10 * s * (u - 0.5)               # 一侧略长
    bottom = ragged_hem(base, n=15, long=(0.06, 0.86), notch=(0.10, 0.70), seed=11)

    def radius_fn(u, v, a, rt=(0.235 * s, 0.160 * s), rb=(0.52 * s, 0.42 * s)):
        e = v ** 1.1
        bil = 1 + (0.10 * math.sin(u * 9.0 + 1.3) + 0.07 * math.sin(u * 17.0 + 4.1) + 0.05 * math.sin(u * 31.0 + 2.0)) * \
            smoothstep(0.08, 1.0, v)                                     # 低频起伏：下摆条带忽内忽外
        return lerp(rt[0], rb[0], e) * bil, lerp(rt[1], rb[1], e) * bil
    holes = [(0.17, 0.56, 0.034, 0.030, 1.0), (0.76, 0.42, 0.044, 0.040, 2.0), (0.30, 0.80, 0.026, 0.034, 3.0),
             (0.88, 0.72, 0.030, 0.026, 4.0), (0.64, 0.64, 0.020, 0.048, 5.0), (0.09, 0.30, 0.028, 0.030, 6.0),
             (0.46, 0.86, 0.022, 0.030, 7.0)]
    cape = RaggedCape("Cape", "Chest", math.pi - 1.35, math.pi + 1.35,
                      top=lambda u: B.z(1.662) - 0.02 * s * abs(math.sin((u - 0.5) * math.pi)), bottom=bottom,
                      r_top=(0.235 * s, 0.160 * s), r_bot=(0.52 * s, 0.42 * s), K=9, cy=-0.02 * s,
                      joints=(0, 0.16, 0.34, 0.52, 0.74, 1.0), flow=0.12 * s, folds=(4.2, 0.004 * s, 0.020 * s), seed=3.3,
                      flare_exp=1.1, radius_fn=radius_fn, holes=holes, slit=(0.5, 0.115, 0.44), zlow=0.0, ztop=B.z(1.662))
    base2 = lambda u: B.z(0.58) + 0.08 * s * (0.5 - u)
    inner = RaggedCape("Cape2_", "Chest", math.pi - 1.20, math.pi + 1.20,
                       top=lambda u: B.z(1.600) - 0.02 * s * abs(math.sin((u - 0.5) * math.pi)),
                       bottom=ragged_hem(base2, n=11, long=(0.05, 0.62), notch=(0.08, 0.50), seed=23),
                       r_top=(0.190 * s, 0.128 * s), r_bot=(0.340 * s, 0.272 * s), K=7, cy=-0.02 * s,
                       joints=(0, 0.16, 0.34, 0.52, 0.74, 1.0), flow=0.08 * s, folds=(3.4, 0.003 * s, 0.014 * s), seed=5.1,
                       flare_exp=1.1, holes=[(0.30, 0.50, 0.040, 0.030, 2.0), (0.70, 0.62, 0.034, 0.040, 4.0)],
                       slit=(0.5, 0.10, 0.40), zlow=0.0, ztop=B.z(1.600))
    front = Panel("TabardF", "Pelvis", B.z(1.140), B.z(0.30), [(0, 0.20 * s), (0.5, 0.18 * s), (1.0, 0.14 * s)],
                  [(0, 0.126 * s), (0.1, 0.140 * s), (0.4, 0.160 * s), (1.0, 0.160 * s)], side=1, point=0.12)
    return cape, front, inner


def build(ctx):
    M = materials(ctx)
    B = marshal_body()
    s = B.s
    for side, label in SIDES:
        hand(ctx, B, side, label, M["bone"], glow=M["glow"] if label == "L" else None, scale=HAND_SC, finger_r=0.0080,
             claw=(M["gold"], 0.018))
    sk = build_skull(ctx, B, M)
    helm = build_helm(ctx, B, M, sk)
    build_spine(ctx, B, M)
    build_ribs(ctx, B, M)
    build_pelvis_bones(ctx, B, M)
    lens = build_core(ctx, B, M)
    build_armor(ctx, B, M)
    build_pauldrons(ctx, B, M)
    build_limbs(ctx, B, M)
    build_gauntlets(ctx, B, M)
    spear = build_spear(ctx, B, M)
    banners = build_banners(ctx, B, M)
    cape, front, inner = cloth(B)
    cape.build(ctx, [M["cape"], M["lining"], M["hem"]], f"{ctx.title} cape", nu=92, nv=48, uv_scale=1.4, thickness=0.022)
    inner.build(ctx, [M["lining"], M["cape"], M["hem"]], f"{ctx.title} cape inner", nu=64, nv=38, uv_scale=1.2, thickness=0.018)
    front.build(ctx, [M["tabard"], M["lining"]], f"{ctx.title} tabard", nu=12, nv=36, thickness=0.016, edges=(M["trim"], 0.0034 * s),
                spine=(M["inlay"], 0.0020 * s))
    clamp_ground(ctx, " boot ")
    thin_trims(ctx)
    tri_report(ctx)
    bbox_report("BOSS3 geo", [o for o, _ in ctx.parts])
    return {"B": B, "sk": sk, "helm": helm, "lens": lens, "spear": spear, "banners": banners, "cape": cape,
            "front": front, "inner": inner}


# ===== 骨架 =====
def skeleton(rig, st):
    B = st["B"]
    s = B.s
    add_skeleton(rig, B)
    hinge, chin = st["sk"]["jaw"]
    rig.bone("Jaw", hinge, chin, "Head", roll=Z)
    for label, e in st["sk"]["eyes"].items():
        rig.bone(f"Eye.{label}", e, e + Vector((0, 0.05 * s, 0)), "Head", roll=Z)
    pb = st["helm"]["plume"]
    rig.bone("Plume", pb, pb + Vector((0, 0, 0.12 * s)), "Head", roll=Y)
    lens = st["lens"]
    rig.bone("CoreGlow", lens, lens + Vector((0, 0.05 * s, 0)), "Chest", roll=Z)
    for k, (b, t, *_rest) in enumerate(poles_def()):
        rig.bone(f"Pole{k}", b, t, "Chest", roll=Y)
        ax = (t - b).normalized()
        orb = t + ax * 0.24
        rig.bone(f"Wisp{k}", orb, orb + Vector((0, 0, 0.25)), f"Pole{k}", roll=Y)
    c0, plen = st["spear"]["pen"]
    A = st["spear"]["A"]
    prev = "Hand.R"
    for i, (j0, j1) in enumerate(((0.0, 0.40), (0.40, 0.78), (0.78, 1.20))):
        rig.bone(f"Pen{i + 1}", c0 - A * j0, c0 - A * j1, prev, roll=st["spear"]["W"])
        prev = f"Pen{i + 1}"
    for g in [st["cape"], st["inner"], st["front"], *st["banners"]]:
        rig.add_garment(g)
    rig.scaled = ["Eye.L", "Eye.R", "Plume", "CoreGlow", "Wisp0", "Wisp1", "Wisp2"]


# ===== 动作 =====
def rest_pole(B, label):
    a = B.arms[label]
    S, E, W = a["shoulder"], a["elbow"], a["wrist"]
    d = (W - S).normalized()
    p = E - S
    return (p - d * p.dot(d)).normalized()


def arm_ik(rig, B, pose, label, target, pole):
    rig.ik2(pose, f"UpperArm.{label}", f"Forearm.{label}", target, pole, rest_pole=rest_pole(B, label))


def hold_spear(rig, st, pose, grip, spear, pole, iters=3):
    """右手握旗枪：给定握点与枪轴方向，反求腕目标做臂 IK，再把手骨对准（手指方向尽量顺着前臂，腕部少折）。"""
    B = st["B"]
    sp = st["spear"]
    A_new = Vector(spear).normalized()
    f_rest = B.hands["R"]["f"]
    rest_frame = frame_from(f_rest, sp["A"])
    fdir = (Vector(grip) - rig.head(pose, "UpperArm.R")).normalized()
    f_new = f_rest
    for _ in range(iters):
        f_new = fdir - A_new * fdir.dot(A_new)
        f_new = f_new.normalized() if f_new.length > 1e-4 else Vector((0, 1, 0))
        d = frame_from(f_new, A_new) @ rest_frame.transposed()
        wrist = Vector(grip) - d @ sp["off"]
        arm_ik(rig, B, pose, "R", wrist, pole)
        fdir = (rig.tail(pose, "Forearm.R") - rig.head(pose, "Forearm.R")).normalized()
    rig.aim(pose, "Hand.R", f_new, up=A_new, rest_up=sp["A"])


def left_hand(rig, st, pose, wrist, pole, fing, palm):
    B = st["B"]
    arm_ik(rig, B, pose, "L", wrist, pole)
    h = B.hands["L"]
    f_new = Vector(fing).normalized()
    up = Vector(palm)
    up = (up - f_new * up.dot(f_new)).normalized()
    rig.aim(pose, "Hand.L", f_new, up=up, rest_up=h["n"])


def tabard_clear(rig, st, pose, extra=0.0):
    """前垂旗按膝盖前移量外掀，屈膝 / 迈步时膝甲不穿出旗面。"""
    B, front = st["B"], st["front"]
    need = 0.05
    for label in ("L", "R"):
        knee = rig.tail(pose, f"Thigh.{label}")
        depth = front.depth(0.5) + 0.02 * B.s
        dz = max(0.2 * B.s, front._top - knee.z)
        need = max(need, math.atan2(knee.y + 0.125 * B.s - depth, dz))
    rig.garment_pose(pose, front, lambda k, j: need + extra)


def accessories(rig, st, p, q, t):
    """军旗、斗篷、前垂旗、下颌、幽火缩放（Idle / Attack / Enrage / Move 共用）。"""
    fan, pb = q["fan"], q["pback"]
    p["Pole0"] = R((X, -pb), (Y, 0.02 * math.sin(t + 0.4) * q["bflut"] / 0.03))
    p["Pole1"] = R((Y, -fan), (X, -pb * 0.8))
    p["Pole2"] = R((Y, fan), (X, -pb * 0.8))
    fl, fu = q["bflare"], q["bflut"]
    for i, g in enumerate(st["banners"]):
        rig.garment_pose(p, g, lambda k, j, i=i: fl + fu * math.sin(2 * t + k * 0.9 + j * 1.1 + i * 1.7),
                         lambda k, j, i=i: 0.6 * fu * math.sin(t + k * 1.3 + j * 0.7 + i))
    # 披风骨链挂在 Chest 上：胸腔后仰时下摆会被带着向前摆进腿里，按胸腔实际后仰角补偿（骨链累加权重和为 2，补偿取 0.55 倍）
    vv = rig.delta(p, "Chest") @ Vector((0, 0, 1))
    tilt = max(0.0, math.atan2(-vv.y, vv.z))
    rig.wind(p, st["cape"], lambda k, j: q["cape"] + 0.55 * tilt + 0.02 * math.sin(t + k * 0.8 + j * 0.9),
             lambda k, j: q["cflare"], lambda k, j: 0.015 * math.sin(t + k * 0.9 + j * 0.6))
    W = st["spear"]["W"]
    for i in range(3):
        p[f"Pen{i + 1}"] = R((W, q["pen"] * (0.5 + 0.25 * i) + q["penf"] * math.sin(2 * t + i * 0.9 + 0.4) * (0.6 + 0.2 * i)))
    rig.wind(p, st["inner"], lambda k, j: 0.85 * q["cape"] + 0.60 * tilt + 0.02 * math.sin(t + k * 1.1 + j * 0.7 + 1.0),
             lambda k, j: 0.8 * q["cflare"], lambda k, j: 0.012 * math.sin(t + k * 0.7 + j * 0.9 + 2.0))
    tabard_clear(rig, st, p, q.get("tab", 0.0))
    p["Jaw"] = R((X, -q["jaw"]))
    fl_ = 1 + 0.06 * math.sin(3 * t)
    p["_scale"] = {"Eye.L": q["eye"] * fl_, "Eye.R": q["eye"] * (1 + 0.06 * math.sin(3 * t + 1.3)),
                   "Plume": q["plume"] * (1 + 0.05 * math.sin(2 * t + 0.5)), "CoreGlow": q["core"],
                   "Wisp0": q["wisp"] * (1 + 0.08 * math.sin(3 * t + 2.0)),
                   "Wisp1": q["wisp"] * (1 + 0.08 * math.sin(3 * t + 0.4)),
                   "Wisp2": q["wisp"] * (1 + 0.08 * math.sin(3 * t + 4.1))}


def pose_from(rig, st, q, t=0.0):
    """由关键参数生成整身姿态（腿 / 臂 IK 逐帧重算，脚始终钉地）。"""
    B = st["B"]
    p = {}
    p["_hover"] = Vector((q["sx"], q["sy"], -q["sink"]))
    lean, tw = q["lean"], q["twist"]
    p["Pelvis"] = R((Z, -tw * 0.35), (Y, q["roll"] * 0.5), (X, -lean * 0.30))
    p["Spine"] = R((Z, -tw * 0.30), (X, -lean * 0.35 + q["arch"] * 0.4))
    p["Chest"] = R((Z, -tw * 0.35), (Y, q["roll"] * 0.5), (X, -lean * 0.35 + q["arch"] * 0.6))
    p["Neck"] = R((X, q["head"] * 0.45), (Z, -q["hyaw"] * 0.5))
    p["Head"] = R((X, q["head"] * 0.55), (Z, -q["hyaw"] * 0.5), (Y, q["shake"]))
    legs = Legs(rig, B)
    for label, off, yaw in (("L", q["lf"], q["yawL"]), ("R", q["rf"], q["yawR"])):
        side = -1 if label == "L" else 1
        a = legs.rest[label]["ankle"] + Vector((off[0], off[1], 0))
        legs.plant(p, label, a, yaw=-side * 0.08 + yaw, knee_out=0.22)
    hold_spear(rig, st, p, q["grip"], q["spear"], q["poleR"])
    left_hand(rig, st, p, q["wristL"], q["poleL"], q["fingL"], q["palmL"])
    fingers(p, B, "R", 0.95)
    fingers(p, B, "L", lambda i: q["curlL"] * (0.7 if i == 0 else 1.0), q["spreadL"])
    accessories(rig, st, p, q, t)
    return p


def neutral(rig, st):
    B = st["B"]
    s = B.s
    a = B.arms["L"]
    hL = B.hands["L"]
    return {"sink": 0.06, "sx": 0.0, "sy": 0.0, "lean": 0.02, "twist": 0.0, "roll": 0.0, "arch": 0.0, "head": -0.04,
            "hyaw": 0.0, "shake": 0.0, "jaw": 0.03, "lf": Vector((0, 0.02, 0)), "rf": Vector((0, -0.02, 0)),
            "yawL": 0.0, "yawR": 0.0,
            "grip": Vector((1.08, 0.72, 2.98)), "spear": Vector((0.03, 0.04, 1.0)), "poleR": Vector((0.55, -0.8, -0.2)),
            "wristL": a["wrist"] + Vector((0.02 * s, 0.03 * s, 0.06 * s)), "poleL": rest_pole(B, "L"),
            "fingL": hL["f"], "palmL": hL["n"], "curlL": 0.35, "spreadL": 0.0,
            "fan": 0.0, "pback": 0.02, "bflare": 0.05, "bflut": 0.03, "cape": 0.04, "cflare": 0.03,
            "eye": 1.0, "plume": 1.0, "core": 1.0, "wisp": 1.0, "tab": 0.0, "pen": 0.0, "penf": 0.10}


def idle_q(rig, st, t):
    q = neutral(rig, st)
    q["sink"] += 0.018 * math.sin(t)
    q["arch"] = 0.018 * math.sin(t + 0.6)
    q["head"] += 0.03 * math.sin(t + 1.4)
    q["hyaw"] = 0.06 * math.sin(t)
    q["roll"] = 0.012 * math.sin(t)
    q["jaw"] = 0.03 + 0.02 * math.sin(2 * t)
    q["spear"] = Vector((0.03 + 0.015 * math.sin(t), 0.04 + 0.01 * math.sin(t + 1), 1.0))
    q["grip"] = q["grip"] + Vector((0, 0, 0.02 * math.sin(t + 0.3)))
    q["wristL"] = q["wristL"] + Vector((0, 0.01 * math.sin(t + 0.8), 0.02 * math.sin(t)))
    q["core"] = 1 + 0.05 * math.sin(2 * t)
    return q


def idle_pose(rig, st, t):
    return pose_from(rig, st, idle_q(rig, st, t), t)


def move_pose(rig, st, t):
    """行军重步：kit gait 慢走参数 + 右手擎旗枪随胸口移动 + 军旗惯性摆。"""
    B = st["B"]
    s = B.s
    p = gait_b3(rig, B, t, stride=0.40, lift=0.12, stance=0.62, bob=0.014, lean=0.06, twist=0.07, arm=0.22, elbow=0.35,
                arm_in=0.10, width=0.012, heel=0.03, knee_out=0.14, head_stab=0.7, sink=0.045, sway=0.012)
    q = neutral(rig, st)
    chest_h0 = rig.SEG["Chest"][0]
    dC = rig.delta(p, "Chest")
    cH = rig.head(p, "Chest")
    grip = cH + dC @ (q["grip"] - chest_h0) + Vector((0, 0, 0.03 * math.sin(2 * t)))
    spear = dC @ Vector((0.03, 0.10 + 0.04 * math.sin(2 * t), 1.0))
    hold_spear(rig, st, p, grip, spear, dC @ q["poleR"])
    fingers(p, B, "R", 0.95)
    fingers(p, B, "L", 0.45)
    p["UpperArm.L"] = R((Y, -0.12), (X, 0.22 * math.sin(t + math.pi)))
    p["Head"] = R((X, -0.02), (Z, 0.04 * math.sin(t)))
    q.update({"pback": 0.06 + 0.02 * math.cos(2 * t), "bflare": 0.14, "bflut": 0.06, "cape": 0.13, "cflare": 0.04,
              "fan": 0.03 * math.sin(t), "jaw": 0.04 + 0.02 * math.sin(2 * t), "tab": 0.03 * math.sin(2 * t + 0.5),
              "core": 1 + 0.05 * math.sin(2 * t)})
    accessories(rig, st, p, q, t)
    return p


def attack_keys(rig, st):
    """举旗枪横扫 → 召唤：1 起势 → 7 高举 → 12 右后引枪 → 16 横扫过前方 → 20 左侧收势 → 26 举枪召唤 → 34 收势。"""
    base = neutral(rig, st)
    raise_ = {"sink": 0.10, "lean": -0.04, "twist": 0.20, "head": 0.12, "arch": 0.05,
              "grip": Vector((1.05, 0.30, 5.05)), "spear": Vector((0.30, -0.25, 1.0)), "poleR": Vector((0.8, -0.3, -0.5)),
              "wristL": Vector((-1.05, 0.75, 3.30)), "fingL": Vector((-0.2, 0.9, 0.3)), "palmL": Vector((0.2, 0.2, 1.0)),
              "curlL": 0.2, "lf": Vector((-0.04, 0.30, 0)), "rf": Vector((0.04, -0.22, 0)), "yawR": -0.3, "eye": 1.15,
              "cape": 0.06, "bflare": 0.10, "pback": 0.04}
    cock = dict(raise_, sink=0.20, lean=0.02, twist=0.42, head=0.02, arch=0.0,
                grip=Vector((1.45, 0.05, 3.95)), spear=Vector((0.88, -0.45, 0.16)), poleR=Vector((0.5, -0.4, -0.8)),
                wristL=Vector((-0.85, 1.25, 3.55)), fingL=Vector((0.1, 1.0, 0.2)), palmL=Vector((0.5, 0.2, 0.3)),
                bflare=0.12, cape=0.08, cflare=0.05)
    sweep = dict(cock, sink=0.26, lean=0.16, twist=-0.18, head=-0.05, roll=-0.04,
                 grip=Vector((0.45, 1.85, 3.55)), spear=Vector((-0.10, 1.0, -0.04)), poleR=Vector((1.0, 0.0, -0.3)),
                 wristL=Vector((-1.10, -0.10, 3.10)), fingL=Vector((-0.3, -0.3, -1.0)), palmL=Vector((-1, 0, 0)),
                 curlL=0.5, bflare=0.30, bflut=0.08, cape=0.20, cflare=0.08, fan=0.06, eye=1.3, sx=-0.06)
    follow = dict(sweep, sink=0.22, lean=0.12, twist=-0.46, roll=-0.06,
                  grip=Vector((-0.80, 1.40, 3.50)), spear=Vector((-0.95, 0.30, 0.04)), poleR=Vector((0.6, -0.2, -0.8)),
                  bflare=0.26, cape=0.16, fan=0.04, sx=-0.10)
    summon = dict(base, sink=0.10, lean=-0.06, twist=0.05, head=0.22, arch=0.08, jaw=0.25,
                  grip=Vector((1.00, 0.55, 5.35)), spear=Vector((0.10, 0.12, 1.0)), poleR=Vector((0.9, -0.3, -0.3)),
                  wristL=Vector((-0.85, 1.35, 4.55)), poleL=Vector((-0.9, -0.2, -0.4)), fingL=Vector((-0.1, 0.35, 1.0)),
                  palmL=Vector((0.0, 1.0, -0.25)), curlL=-0.05, spreadL=0.8, lf=Vector((-0.02, 0.12, 0)),
                  rf=Vector((0.03, -0.10, 0)), eye=1.55, plume=1.4, core=1.3, wisp=1.6, bflare=0.22, bflut=0.07,
                  fan=0.10, cape=0.10, cflare=0.06)
    return with_defaults(base, [(1, {}, "io"), (7, raise_, "io"), (12, cock, "io"), (16, sweep, "in"),
                                (20, follow, "out"), (26, summon, "io"), (34, {}, "io")])


def enrage_keys(rig, st):
    """军旗展开、幽光大盛：1 → 10 收势蓄力（幽火内敛）→ 18 仰天展臂（旗架外张、旗面翻卷、幽火暴涨）
    → 26 / 36 持续咆哮 → 44 回落 → 49 收势。"""
    base = neutral(rig, st)
    gather = {"sink": 0.24, "lean": 0.26, "head": -0.28, "twist": 0.0, "jaw": 0.05,
              "grip": Vector((0.80, 1.05, 3.05)), "spear": Vector((0.12, 0.45, 1.0)), "poleR": Vector((0.8, -0.4, -0.3)),
              "wristL": Vector((-0.40, 0.80, 3.75)), "poleL": Vector((-1.0, -0.2, -0.3)), "fingL": Vector((0.7, 0.3, 0.3)),
              "palmL": Vector((0.2, -1.0, 0.0)), "curlL": 1.1, "lf": Vector((-0.06, 0.08, 0)), "rf": Vector((0.06, -0.06, 0)),
              "eye": 0.7, "plume": 0.7, "core": 0.8, "wisp": 0.6, "fan": -0.04, "pback": 0.0, "bflare": 0.03,
              "cape": 0.05}
    roar = {"sink": -0.02, "lean": -0.20, "arch": 0.12, "head": 0.30, "jaw": 0.50, "twist": 0.0,
            "grip": Vector((1.00, 0.35, 5.75)), "spear": Vector((0.14, 0.10, 1.0)), "poleR": Vector((1.0, -0.3, -0.2)),
            "wristL": Vector((-1.85, 0.55, 5.00)), "poleL": Vector((-0.4, -1.0, -0.6)), "fingL": Vector((-0.6, 0.2, 0.8)),
            "palmL": Vector((-0.3, 1.0, 0.3)), "curlL": -0.08, "spreadL": 1.0,
            "lf": Vector((-0.10, 0.10, 0)), "rf": Vector((0.10, -0.08, 0)),
            "eye": 1.8, "plume": 2.0, "core": 1.6, "wisp": 2.6, "fan": 0.30, "pback": 0.12, "bflare": 0.42,
            "bflut": 0.12, "cape": 0.26, "cflare": 0.12}
    roar2 = dict(roar, head=0.34, eye=1.95, plume=2.2, wisp=2.8, bflare=0.46, fan=0.32)
    roar3 = dict(roar2, head=0.31, eye=1.9, bflare=0.40)
    settle = dict(base, eye=1.3, plume=1.2, core=1.1, wisp=1.3, fan=0.06, bflare=0.12, cape=0.08)
    return with_defaults(base, [(1, {}, "io"), (10, gather, "io"), (18, roar, "back"), (26, roar2, "out"),
                                (36, roar3, "lin"), (44, settle, "io"), (49, {}, "io")])


def animate(rig, st):
    loop(rig, "Idle", 96, lambda t: idle_pose(rig, st, t), step=2)
    loop(rig, "Move", 40, lambda t: move_pose(rig, st, t), step=1)
    ak = attack_keys(rig, st)
    sampled(rig, "Attack", 33, lambda f: pose_from(rig, st, track(ak, f), (f - 1) * 0.35))
    ek = enrage_keys(rig, st)

    def enrage(f):
        q = track(ek, f)
        if 18 <= f <= 40:                                  # 咆哮震颤与旗面猛烈翻动
            amp = smoothstep(18, 21, f) * (1 - smoothstep(36, 40, f))
            q["shake"] += 0.035 * math.sin(f * 2.1) * amp
            q["lean"] += 0.02 * math.sin(f * 1.7) * amp
            q["jaw"] += 0.06 * math.sin(f * 1.9) * amp
        return pose_from(rig, st, q, (f - 1) * 0.45)
    sampled(rig, "Enrage", 48, enrage)
    ground_check(rig, CLIPS, [f"Toe.{s}" for s in "LR"] + [f"Foot.{s}" for s in "LR"])
    seam_check(rig, ("Idle", "Move"))
