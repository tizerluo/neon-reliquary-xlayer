"""塞拉芙 · 赤红战地牧师（Seraph, The Crimson Chaplain）。

设定：振翼悬浮的战地牧师。绯红漆甲 + 象牙骨瓷（玫瑰金金缮开片）+ 玫瑰金滚边，玫红自发光只占小面积。
标志件：背后“圣骸引擎”挂三对机械刃羽翼（每翼三节骨，刃羽刚性绑在各节上）；骨瓷面甲 + 面纱 + 玫瑰金尖刺冠
（不是光环——光环属于尼克斯）；层叠长袍（象牙符文内裙 + 绯红开襟外袍 + 后垂饰）、玫瑰金雕花腰封 + 绯红短甲裙
+ 腰间垂链与圣徽垂片；绯红分层肩甲、护臂与铠甲手、斜挎象牙圣带；胸前发光的“生命圣杯”。
动作：Idle（悬浮缓振）/ Move（前倾滑翔 + 振翼）/ Cast（莲华新生：双掌前推、群翼前扫）/
Channel（刃花绽放：双臂上扬、群翼全展高举，13–28 帧保持）。
网页端节点：SERAPH_BLADE（展示页环绕的花瓣刃，只进展示版）。
"""

import math

import bmesh
from mathutils import Vector

from kit.core import (TAU, apply_all, bands, bm_object, chain, circuit_maps, clamp, ellipsoid, filigree_maps, finish,
                      garment, gem, interp, invdist, join, lathe, lerp, orient, plate, projector, rigid,
                      smoothstep, solidify, spike, surface, trim, tube)
from kit.garment import Panel, Wrap, cloth_fold
from kit.humanoid import SIDES, Body, add_skeleton, hand, rerebrace, shell, suit_arm, suit_leg, suit_torso, vambrace
from kit.motion import fingers
from kit.rig import R, X, Y, Z

from chars._grace_helpers import (Clearance, cloth_edges, craquelure_maps, dangle2, feather_outline, gem2, gorget2,
                                  hem_line, hem_rune_maps, keyed_samples, pauldron2, petal_outline, radial_wrap)
from chars._seraph2_parts import (axis_out, chain_links, embroidered_silk_maps, feather_width, gem_lo, rims, root_sheath, stole,
                                  stole_maps, sunburst, swag, tassets, vein, wrap_base)

TITLE = "Seraph"
ACCENT = (1.0, 0.56, 0.66)
CLIPS = ("Idle", "Move", "Cast", "Channel")
GAME_TRIS = 64000
REVIEW_POSE = ("Idle", 1)
ROSE = ACCENT
J5 = (0, 0.16, 0.34, 0.52, 0.74, 1.0)


def materials(ctx):
    M = ctx.M
    # 配色目标：饱和绯红 + 干净象牙白 + 亮玫瑰金，三者明度拉开；发光只留给细线与宝石
    crimson = (0.46, 0.014, 0.036)
    ctx.mat("lacquer", "crimson lacquer plate", crimson, metal=0.30, rough=0.20, coat=1.0, spec=0.45)
    ctx.texture("lacquer", filigree_maps(crimson, (0.20, 0.006, 0.016), size=1024, seed=8, density=22, width=1),
                normal_strength=0.35)
    ivory = (0.90, 0.84, 0.74)
    ctx.mat("ivory", "ivory bone ceramic", ivory, rough=0.28, coat=0.6, spec=0.5)
    ctx.texture("ivory", craquelure_maps(ivory, (0.86, 0.50, 0.40), size=1024, seed=5, cells=9, fine=0.35),
                normal_strength=0.4)
    rose_gold = (0.98, 0.62, 0.50)
    ctx.mat("trim", "rose-gold trim", rose_gold, metal=1.0, rough=0.18)
    ctx.mat("gilt", "rose-gold gilt", rose_gold, metal=1.0, rough=0.24)
    ctx.mat("cincher", "rose-gold filigree cincher", rose_gold, metal=1.0, rough=0.26)
    ctx.texture("cincher", filigree_maps(rose_gold, (0.46, 0.20, 0.15), size=1024, seed=12, density=20, width=1),
                normal_strength=0.45)
    ctx.mat("suit", "wine undersuit", (0.060, 0.006, 0.012), metal=0.2, rough=0.5, sheen=0.15,
            sheen_tint=(0.9, 0.2, 0.3))
    robe = (0.34, 0.010, 0.030)
    ctx.mat("robe", "crimson velvet robe", robe, rough=0.60, sheen=0.15, sheen_tint=(1.0, 0.10, 0.18), spec=0.20)
    ctx.texture("robe", circuit_maps(ROSE, base_rgb=robe, line_rgb=(0.42, 0.03, 0.07), size=2048, seed=41, buses=12,
                                     reach=(0.32, 0.78)), emit_strength=1.9)
    silk = (0.86, 0.80, 0.70)
    ctx.mat("silk", "ivory rune silk", silk, rough=0.50, sheen=0.20, sheen_tint=(1, 0.85, 0.85), spec=0.35)
    ctx.texture("silk", embroidered_silk_maps(ROSE, silk, (0.50, 0.04, 0.08), size=1024, seed=17), emit_strength=2.0)
    ctx.mat("stole", "ivory rune stole", silk, rough=0.5, sheen=0.2, sheen_tint=(1, 0.85, 0.85), spec=0.3)
    ctx.texture("stole", stole_maps(ROSE, silk, (0.55, 0.10, 0.13), size=512, cols=3), emit_strength=1.8)
    ctx.mat("lining", "wine satin lining", (0.13, 0.006, 0.018), rough=0.38, sheen=0.35, sheen_tint=(1, 0.2, 0.3))
    veil = (0.36, 0.012, 0.032)
    ctx.mat("veil", "crimson veil gauze", veil, rough=0.5, sheen=0.20, sheen_tint=(1, 0.2, 0.3), spec=0.3)
    ctx.texture("veil", hem_rune_maps(ROSE, veil, line_rgb=(0.62, 0.14, 0.16), size=1024, seed=29, band=0.10,
                                      cols=22), emit_strength=1.8)
    ctx.mat("glow", "rose core glow", (1.0, 0.6, 0.7), emit=ROSE, strength=8.0)
    ctx.mat("inlay", "rose circuit inlay", (0.6, 0.3, 0.35), emit=ROSE, strength=3.2)
    # 象牙刃羽上的羽脉：粉白发光在象牙底上读不出来，改用更饱和的洋红，强度压低
    ctx.mat("vein", "magenta vein inlay", (0.55, 0.02, 0.10), emit=(1.0, 0.10, 0.32), strength=2.2)
    ctx.mat("hem", "rose hem light", (0.5, 0.25, 0.3), emit=ROSE, strength=4.5)
    ctx.mat("blade", "rose petal crystal", (0.35, 0.03, 0.06), metal=0.6, rough=0.12, coat=1.0)
    return M


# ===== 头部：骨瓷面甲、面纱、玫瑰金尖刺冠 =====
HEAD_PROXY = (0.086, 0.097, 0.124)
VEIL_OPEN = [(0.0, 0.08), (0.14, 0.44), (0.26, 0.98), (0.45, 1.10), (0.62, 1.16), (0.80, 1.24), (1.0, 1.30)]


def build_face(ctx, B, M):
    s = B.s
    hc = B.head_c
    ctx.part(ellipsoid(f"{ctx.title} head", hc - Vector((0, 0.010 * s, 0)), (0.078 * s, 0.080 * s, 0.114 * s),
                       [M["suit"]], 28, 18), rigid("Head"))
    c = hc + Vector((0, 0.030 * s, -0.004 * s))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=72, v_segments=48, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.10], context="VERTS")
    for v in bm.verts:
        x, y, z = v.co
        if z < 0:                                   # 下颌收成柔和的小尖下巴（圆润的瓷偶脸）
            z *= 0.98
            k = (-z) ** 1.6
            x *= max(0.34, 1 - 0.40 * k)
            y += 0.08 * k * max(0.0, y)
        front = max(0.0, y)
        ax = abs(x)
        ridge = 0.26 * math.exp(-(x / 0.13) ** 2) * smoothstep(-0.34, -0.04, z) * (1 - smoothstep(0.10, 0.26, z))
        nose = (ridge + 0.10 * math.exp(-(x / 0.16) ** 2 - ((z + 0.27) / 0.06) ** 2)) * front ** 3
        brow = 0.050 * math.exp(-((z - 0.24) / 0.07) ** 2) * front
        socket = -0.070 * math.exp(-((ax - 0.34) / 0.14) ** 2 - ((z - 0.10) / 0.080) ** 2) * front
        cheek = 0.045 * math.exp(-((ax - 0.44) / 0.15) ** 2 - ((z + 0.14) / 0.12) ** 2) * front
        lips = (0.040 * math.exp(-(x / 0.15) ** 2 - ((z + 0.43) / 0.040) ** 2)
                - 0.018 * math.exp(-(x / 0.13) ** 2 - ((z + 0.40) / 0.010) ** 2)) * front
        v.co = Vector((x * 0.072 * s, (y + nose + brow + socket + cheek + lips) * 0.058 * s, z * 0.102 * s)) + c
    face = bm_object(f"{ctx.title} face", bm, [M["ivory"]])
    orient(face, lambda q: hc)
    face = finish(face, 0.004 * s, -1, 0)
    ctx.part(face, rigid("Head"))
    proj = projector(face, (0, -1, 0))
    # 合目：两道下弯的发光睫线，读作安详的闭目
    eye_z = c.z + 0.0105 * s
    for sd in (-1, 1):
        pts = [proj(Vector((sd * (0.0125 + i / 12 * 0.0250) * s, 1.0,
                            eye_z - 0.0036 * s * (1 - ((i / 12 - 0.5) / 0.5) ** 2))), 0.0010 * s) for i in range(13)]
        ctx.part(tube(f"{ctx.title} eye {sd}", pts, [0.0014 * s] * 13, [M["glow"]], n=6), rigid("Head"))
    # 左眼下一滴发光泪珠 + 额心玫瑰金竖纹
    ctx.part(gem(f"{ctx.title} tear", proj(Vector((-0.026 * s, 1.0, eye_z - 0.018 * s)), 0.0018 * s), 0.0034 * s,
                 M["glow"], (0.7, 0.5, 1.2)), rigid("Head"))
    brow_line = [proj(Vector((0, 1.0, eye_z + 0.018 * s + i * 0.0045 * s)), 0.0010 * s) for i in range(8)]
    ctx.part(tube(f"{ctx.title} brow mark", brow_line, [0.0016 * s] * 8, [M["trim"]], n=6), rigid("Head"))
    # 绯红漆唇
    lip_z = c.z - 0.0440 * s
    for dz, w in ((0.0030, 0.0095), (-0.0032, 0.0085)):
        p = proj(Vector((0, 1.0, lip_z + dz * s)), -0.0012 * s)
        ctx.part(ellipsoid(f"{ctx.title} lip {dz}", p, (w * s, 0.0032 * s, 0.0030 * s), [M["lacquer"]], 16, 8),
                 rigid("Head"))
    # 金缮裂痕：一道玫瑰金细裂从右额经眼角落到颊边，暗示历经战火的骨瓷
    crack = [(0.030, 0.070), (0.036, 0.052), (0.031, 0.038), (0.040, 0.022), (0.036, 0.006), (0.044, -0.012),
             (0.041, -0.030), (0.048, -0.046)]
    pts = [proj(Vector((x * s, 1.0, c.z + z * s)), 0.0006 * s) for x, z in crack]
    ctx.part(tube(f"{ctx.title} kintsugi", pts, [0.0006 * s, 0.0011 * s, 0.0013 * s, 0.0012 * s, 0.0011 * s,
                                                 0.0010 * s, 0.0008 * s, 0.0], [M["trim"]], n=6, per=3),
             rigid("Head"))
    # 护颈头巾（修女式 wimple）：填满面甲与护喉之间的颈部，下巴内收藏住上沿
    ctx.part(tube(f"{ctx.title} wimple", [(0, 0.002 * s, B.z(1.690)), (0, 0.006 * s, B.z(1.735)),
                                         (0, 0.010 * s, B.z(1.775))],
                  [0.064 * s, 0.058 * s, 0.050 * s], [M["veil"]], n=28),
             bands([(B.z(1.78), "Head"), (B.z(1.72), "Neck"), (B.z(1.68), "Chest")]))
    return face


def veil_point_fn(B):
    s = B.s
    hc = B.head_c
    rx0, ry0, rz0 = (k * s for k in HEAD_PROXY)
    z_top = hc.z + rz0 + 0.016 * s
    z_jaw = B.z(1.80)

    def hug(z):
        k = clamp((z - hc.z) / rz0, -1, 1)
        f = math.sqrt(max(0.0, 1 - k * k))
        return rx0 * f, ry0 * f
    jx, jy = hug(z_jaw)

    def point(u, v):
        op = interp(VEIL_OPEN, v)
        a = op + u * (TAU - 2 * op)
        back = max(0.0, -math.cos(a))
        z_bot = lerp(B.z(1.705), B.z(1.600), back ** 0.9)
        z = lerp(z_top, z_bot, v)
        room = 0.014 * s + 0.016 * s * back ** 1.5          # 脑后留出蓬松的余量
        if z >= z_jaw:
            hx, hy = hug(z)
            rx, ry, fall = max(hx, 0.006 * s) + room, max(hy, 0.006 * s) + room, 0.0
        else:
            fall = smoothstep(z_jaw, z_bot, z)
            rx = lerp(jx + room, 0.132 * s, fall ** 0.8)
            ry = lerp(jy + room, 0.160 * s, fall ** 0.8)
        fold = cloth_fold(a, v, 9.0, 0.0018 * s + 0.016 * s * fall, 1.3)
        return Vector(((rx + fold) * math.sin(a), hc.y + (ry + fold) * math.cos(a) - 0.016 * s * fall, z))
    return point


def build_veil(ctx, B, M):
    s = B.s
    point = veil_point_fn(B)
    veil = surface(f"{ctx.title} veil", point, 60, 38, [M["veil"], M["lining"]], uvfn=lambda u, v: (u * 1.4, 1 - v))
    orient(veil, lambda c: Vector((0, B.head_c.y, c.z)))
    solidify(veil, 0.0045 * s, 0, inner_offset=1)
    spec = bands([(B.z(1.80), "Head"), (B.z(1.72), "Neck"), (B.z(1.655), "Chest")])
    ctx.part(apply_all(veil), spec)
    hem = [point(i / 80, 1.0) for i in range(81)]
    hem = [p + Vector((p.x, p.y - B.head_c.y, 0)).normalized() * 0.004 * s for p in hem]
    ctx.part(trim(f"{ctx.title} veil hem", hem, 0.0024 * s, M["hem"], n=4), spec)
    for u in (0.0, 1.0):
        edge = [point(u, 0.10 + j / 26 * 0.90) for j in range(27)]
        edge = [p + Vector((p.x, p.y - B.head_c.y, 0)).normalized() * 0.003 * s for p in edge]
        ctx.part(trim(f"{ctx.title} veil edge {u}", edge, 0.0026 * s, M["trim"], n=5), spec)
    return veil


def build_crown(ctx, B, M, face, veil):
    s = B.s
    hc = B.head_c
    hit = radial_wrap([face, veil], (0, hc.y, 0))
    zb = lambda a: hc.z + 0.058 * s + 0.010 * s * (1 - math.cos(a)) / 2      # 冠带前低后高
    band = [hit(i / 56 * TAU, zb(i / 56 * TAU), 0.004 * s) for i in range(56)]
    ctx.part(trim(f"{ctx.title} crown band", band, 0.0042 * s, M["trim"], closed=True, n=5), rigid("Head"))
    band2 = [hit(i / 44 * TAU, zb(i / 44 * TAU) - 0.009 * s, 0.003 * s) for i in range(44)]
    ctx.part(trim(f"{ctx.title} crown band low", band2, 0.0024 * s, M["trim"], closed=True, n=4), rigid("Head"))
    # 尖刺：正前最长、左右交替长短、向后渐短，刃状扁刺向上外张
    count = 19
    mids = []
    for k in range(count):
        a = (k / count) * TAU
        front = max(0.0, math.cos(a))
        major = k % 2 == 0
        L = (0.050 + 0.125 * front ** 1.6) * (1.0 if major else 0.55) * s
        base = hit(a, zb(a) + 0.002 * s, 0.002 * s)
        out = Vector((math.sin(a), math.cos(a), 0))
        el = math.radians(lerp(52, 72, front))
        d = (out * math.cos(el) + Vector((0, 0, 1)) * math.sin(el)).normalized()
        tip = base + d * L
        ctx.part(spike(f"{ctx.title} crown spike {k}", base, tip, (0.0130 if major else 0.0080) * s, [M["gilt"]],
                       sides=4, fx=1.0, fy=0.45, up=tuple(out)), rigid("Head"))
        mids.append(base + d * min(L, 0.05 * s) * 0.55)
        if major and front > 0.3:
            ctx.part(gem_lo(f"{ctx.title} crown gem {k}", base + out * 0.004 * s + Vector((0, 0, 0.004 * s)),
                         0.0042 * s, M["glow"], (0.8, 0.6, 1.3)), rigid("Head"))
    ctx.part(trim(f"{ctx.title} crown arc", mids, 0.0018 * s, M["trim"], closed=True), rigid("Head"))
    # 额前主宝石：心形玫瑰光 + 玫瑰金托
    fc = hit(0.0, zb(0.0) + 0.004 * s, 0.006 * s)
    ctx.part(ellipsoid(f"{ctx.title} crown setting", fc - Vector((0, 0.002 * s, 0)), (0.016 * s, 0.006 * s, 0.018 * s),
                       [M["gilt"]], 18, 10), rigid("Head"))
    ctx.part(gem(f"{ctx.title} crown heart", fc + Vector((0, 0.004 * s, 0.001 * s)), 0.010 * s, M["glow"],
                 (0.95, 0.55, 1.2)), rigid("Head"))


# ===== 铠甲手：手背玫瑰金护板 + 宝石 =====
def gauntlet_plate(ctx, B, side, label, M, scale):
    s = B.s
    h = B.hands[label]
    f, n, sv, w = h["f"], h["n"], h["s"], h["wrist"]
    back = -n                                         # 掌心朝 n，手背朝 -n
    na = f.cross(sv).normalized()
    sg = 1.0 if na.dot(back) > 0 else -1.0
    k = scale * s
    outline = [(-0.004 * k, -0.017 * k), (0.030 * k, -0.023 * k), (0.066 * k, -0.019 * k), (0.084 * k, 0.0),
               (0.066 * k, 0.019 * k), (0.030 * k, 0.023 * k), (-0.004 * k, 0.017 * k)]
    origin = w + back * 0.0165 * k
    bulge = lambda x, y: sg * 0.006 * k * (1 - min(1.0, (y / (0.024 * k)) ** 2))
    ctx.part(plate(f"{ctx.title} gauntlet plate {label}", outline, 0.0040 * k, [M["gilt"]], origin=origin, xaxis=f,
                   yaxis=sv, bulge=bulge, bev=0.0008 * k, bev_seg=1), rigid(f"Hand.{label}"))
    ctx.part(gem_lo(f"{ctx.title} gauntlet gem {label}", origin + f * 0.036 * k + back * 0.0095 * k, 0.0060 * k,
                  M["glow"], (1, 1, 1)), rigid(f"Hand.{label}"))


# ===== 胸前生命圣杯 =====
def build_chalice(ctx, B, M, cuirass):
    s = B.s
    proj = projector(cuirass, (0, -1, 0))
    top, bot, W = B.z(1.652), B.z(1.515), 0.058 * s

    def plaque(u, v):
        z = lerp(top, bot, v)
        w = W * math.sin(math.pi * lerp(0.03, 0.97, v)) ** 0.75
        return proj(Vector(((2 * u - 1) * w, 1.0, z)), 0.0030 * s)
    pl = surface(f"{ctx.title} chalice plaque", plaque, 22, 26, [M["ivory"]])
    orient(pl, lambda c: Vector((0, 0, c.z)))
    ctx.part(finish(pl, 0.0035 * s, 1, 0), rigid("Chest"))
    rim = [plaque(0.0, j / 20) for j in range(21)] + [plaque(1.0, j / 20) for j in range(20, -1, -1)]
    rim = [proj(Vector((p.x, 1.0, p.z)), 0.0062 * s) for p in rim]
    ctx.part(trim(f"{ctx.title} chalice plaque rim", rim, 0.0026 * s, M["trim"], closed=True, n=5), rigid("Chest"))
    cz = lerp(top, bot, 0.40)
    front = proj(Vector((0, 1.0, cz)), 0.0) + Vector((0, 0.013 * s, 0))
    ks = 1.3
    prof = [(0.020, 0.030), (0.022, 0.024), (0.018, 0.010), (0.010, 0.002), (0.004, -0.004), (0.0035, -0.020),
            (0.0075, -0.025), (0.0035, -0.030), (0.004, -0.038), (0.015, -0.046), (0.016, -0.050), (0.001, -0.051)]
    cup = lathe(f"{ctx.title} chalice", [(r * ks * s, z * ks * s) for r, z in prof], [M["gilt"]], segments=24,
                center=(front.x, front.y, front.z))
    ctx.part(finish(cup, 0.0020 * s, 0, 0), rigid("Chest"))
    ctx.part(ellipsoid(f"{ctx.title} chalice light", front + Vector((0, 0, 0.024 * ks * s)),
                       (0.0175 * ks * s, 0.0175 * ks * s, 0.0035 * s), [M["glow"]], 16, 8), rigid("Chest"))
    ctx.part(gem(f"{ctx.title} chalice heart", front + Vector((0, 0.004 * s, 0.047 * ks * s)), 0.0085 * s, M["glow"],
                 (0.9, 0.6, 1.25)), rigid("Chest"))
    # 圣杯两侧放射的光线嵌线：贴胸甲表面向锁骨、肋侧延伸（高度夹在领口以下，投射落空的点直接丢弃）
    zmax = B.z(1.648)
    for k, ang in enumerate((0.95, 1.35, 1.80, 2.30)):
        for sd in (-1, 1):
            pts = []
            for i in range(10):
                r = (0.062 + i * 0.0105) * s
                p = Vector((sd * math.sin(ang) * r, 1.0, min(zmax, cz + math.cos(ang) * r * 0.9)))
                q = proj(p, 0.0022 * s)
                if q.y < 0.9:
                    pts.append(q)
            if len(pts) < 4:
                continue
            ctx.part(trim(f"{ctx.title} chalice ray {k}{sd}", pts, 0.0016 * s, M["inlay"]), rigid("Chest"))
            ctx.part(ellipsoid(f"{ctx.title} chalice ray via {k}{sd}", pts[-1], (0.0036 * s,) * 3, [M["glow"]], 8, 6),
                     rigid("Chest"))


# ===== 圣骸引擎与三对刃羽翼 =====
WINGS = (
    # z：翼根高度（身高比例），elev：首节仰角，bend：逐节仰角变化，back：后掠角，lens：三节骨长，
    # blades：刃羽数，lmin/lmax：最短 / 最长羽长，width：羽宽
    dict(z=1.555, x=0.070, elev=50.0, bend=-16.0, back=22.0, lens=(0.21, 0.24, 0.22), blades=13, lmin=0.15,
         lmax=0.45, width=0.056, coverts=6, cov=1.0),
    dict(z=1.470, x=0.080, elev=14.0, bend=-12.0, back=30.0, lens=(0.18, 0.21, 0.19), blades=11, lmin=0.13,
         lmax=0.37, width=0.052, coverts=5, cov=0.92),
    dict(z=1.385, x=0.075, elev=-16.0, bend=-8.0, back=38.0, lens=(0.13, 0.15, 0.14), blades=8, lmin=0.10,
         lmax=0.27, width=0.046, coverts=4, cov=0.80),
)
HARNESS_Y = -0.205


def wing_frame(B, p, side):
    cfg = WINGS[p]
    s = B.s
    root = Vector((side * cfg["x"] * s, HARNESS_Y * s, B.z(cfg["z"])))
    pts, dirs = [root], []
    b = math.radians(cfg["back"])
    for j, L in enumerate(cfg["lens"]):
        e = math.radians(cfg["elev"] + cfg["bend"] * j)
        d = Vector((side * math.cos(e) * math.cos(b), -math.sin(b), math.sin(e) * math.cos(b))).normalized()
        dirs.append(d)
        pts.append(pts[-1] + d * L * s)
    davg = (pts[-1] - pts[0]).normalized()
    n = davg.cross(Z).normalized()             # 抬翼轴：绕它正转即上抬
    nb = n if n.y < 0 else -n                  # 指向身后的翼面法线，刃羽沿它分层
    return pts, dirs, n, nb


def build_harness(ctx, B, M):
    s = B.s
    hy = HARNESS_Y * s
    spec = rigid("Wings")
    ctx.part(tube(f"{ctx.title} engine spine", [(0, hy, B.z(1.585)), (0, hy - 0.006 * s, B.z(1.470)),
                                               (0, hy, B.z(1.330))],
                  [0.011 * s, 0.017 * s, 0.010 * s], [M["gilt"]], n=12), spec)
    ctx.part(spike(f"{ctx.title} engine tail", (0, hy, B.z(1.335)), (0, hy + 0.01 * s, B.z(1.270)), 0.009 * s,
                   [M["gilt"]], sides=6), spec)
    # 生命核心：竖直发光胶囊 + 玫瑰金笼
    core = Vector((0, hy - 0.022 * s, B.z(1.470)))
    ctx.part(ellipsoid(f"{ctx.title} engine core", core, (0.014 * s, 0.010 * s, 0.040 * s), [M["glow"]], 16, 12), spec)
    for k in range(4):
        a = k / 4 * TAU + math.pi / 4
        o = Vector((math.cos(a) * 0.020 * s, math.sin(a) * 0.014 * s, 0))
        ctx.part(tube(f"{ctx.title} engine cage {k}", [core + o * 0.4 + Vector((0, 0, 0.052 * s)), core + o * 1.2,
                                                        core + o * 0.4 - Vector((0, 0, 0.052 * s))],
                      [0.0024 * s] * 3, [M["trim"]], n=6), spec)
    for p, cfg in enumerate(WINGS):
        z = B.z(cfg["z"])
        ctx.part(ellipsoid(f"{ctx.title} engine vertebra {p}", (0, hy - 0.004 * s, z), (0.040 * s, 0.020 * s, 0.022 * s),
                           [M["ivory"]], 18, 10), spec)
        for side, label in SIDES:
            hub = Vector((side * cfg["x"] * s, hy, z))
            ctx.part(tube(f"{ctx.title} engine bar {p}{label}", [(0, hy, z), hub], [0.0085 * s, 0.0075 * s],
                          [M["gilt"]], n=8, per=1), spec)
            ctx.part(ellipsoid(f"{ctx.title} engine hub {p}{label}", hub, (0.024 * s,) * 3, [M["gilt"]], 14, 8), spec)
            ctx.part(gem_lo(f"{ctx.title} engine hub gem {p}{label}", hub + Vector((side * 0.010 * s, -0.018 * s, 0)),
                         0.0075 * s, M["glow"], (1, 0.7, 1)), spec)
            back = B.torso_point(math.pi - side * 0.55, z, 0.010 * s)
            ctx.part(tube(f"{ctx.title} engine strut {p}{label}", [back, hub.lerp(back, 0.35), hub],
                          [0.0080 * s, 0.0068 * s, 0.0060 * s], [M["lacquer"]], n=8), spec)


def build_wing(ctx, B, M, p, side, label, clear):
    cfg = WINGS[p]
    s = B.s
    pts, dirs, n, nb = wing_frame(B, p, side)
    bones = [f"Wing{p}{label}.{j}" for j in (1, 2, 3)]
    lens = [L * s for L in cfg["lens"]]
    cum = [0.0, lens[0], lens[0] + lens[1], sum(lens)]
    total = cum[-1]
    # 翼臂（机械翼骨）：每节一段玫瑰金骨管 + 下侧平行液压副杆 + 箍环；上缘绯红漆甲护条 + 发光嵌线；
    # 关节为玫瑰金轴承球 + 双侧宝石，挂在子骨上
    for j in range(3):
        r0, r1 = lerp(0.018, 0.009, j / 3) * s, lerp(0.018, 0.009, (j + 1) / 3) * s
        a, b = pts[j], pts[j + 1]
        ctx.part(tube(f"{ctx.title} wing arm {p}{label}{j}", [a, b], [r0, r1], [M["gilt"]], n=8, per=1),
                 rigid(bones[j]))
        up = dirs[j].cross(nb).normalized()
        if up.z < 0:
            up = -up
        L = (b - a).length
        guard = [(0.0, -0.004 * s), (L * 0.15, 0.012 * s), (L * 0.85, 0.010 * s), (L * 1.02, 0.0),
                 (L * 0.85, -0.006 * s), (L * 0.15, -0.008 * s)]
        ctx.part(plate(f"{ctx.title} wing guard {p}{label}{j}", guard, 0.011 * s, [M["lacquer"]],
                       origin=a + up * (r0 * 0.9) - nb * 0.002 * s, xaxis=dirs[j], yaxis=up, bev=0.0015 * s,
                       bev_seg=1), rigid(bones[j]))
        ctx.part(trim(f"{ctx.title} wing guard rim {p}{label}{j}",
                      [a + dirs[j] * x + up * (r0 * 0.9 + y + 0.0012 * s) - nb * 0.002 * s
                       for x, y in guard[1:4]], 0.0018 * s, M["trim"], n=5), rigid(bones[j]))
        line = [a.lerp(b, t) + up * (r0 * 0.9 + 0.0060 * s) - nb * 0.0078 * s for t in (0.14, 0.5, 0.84)]
        ctx.part(trim(f"{ctx.title} wing inlay {p}{label}{j}", line, 0.0017 * s, M["inlay"], n=5), rigid(bones[j]))
        # 液压副杆：翼骨下方一根更细的玫瑰金杆，两端各一个小轴套
        rod = [a.lerp(b, t) - up * (r0 * 1.9) for t in (0.10, 0.90)]
        ctx.part(tube(f"{ctx.title} wing rod {p}{label}{j}", rod, [r0 * 0.42, r0 * 0.36], [M["gilt"]], n=6, per=1),
                 rigid(bones[j]))
        for t, q in ((0.10, rod[0]), (0.90, rod[1])):
            ctx.part(tube(f"{ctx.title} wing link {p}{label}{j}{t}", [a.lerp(b, t), q], [r0 * 0.34, r0 * 0.34],
                          [M["gilt"]], n=5, per=1), rigid(bones[j]))
        c = a.lerp(b, 0.5)
        ring = [c + (up * math.cos(k / 8 * TAU) + nb * math.sin(k / 8 * TAU)) * lerp(r0, r1, 0.5) * 1.28
                for k in range(8)]
        ctx.part(trim(f"{ctx.title} wing band {p}{label}{j}", ring, 0.0030 * s, M["trim"], closed=True, n=4),
                 rigid(bones[j]))
        if j > 0:
            ctx.part(ellipsoid(f"{ctx.title} wing knuckle {p}{label}{j}", a, (r0 * 1.55,) * 3, [M["gilt"]], 12, 8),
                     rigid(bones[j]))
            for sg in (-1, 1):
                ctx.part(gem_lo(f"{ctx.title} wing knuckle gem {p}{label}{j}{sg}", a + nb * sg * r0 * 1.40,
                              0.0062 * s, M["glow"], (1, 0.55, 1)), rigid(bones[j]))
        for t in (0.35, 0.7, 1.0):
            clear.point(bones[j], a.lerp(b, t), f"wing{p}{label} arm")
    ctx.part(spike(f"{ctx.title} wing tip {p}{label}", pts[3], pts[3] + dirs[2] * 0.07 * s, 0.009 * s, [M["gilt"]],
                   sides=4, fx=1.0, fy=0.5, up=tuple(nb)), rigid(bones[2]))
    def station(sv):
        """沿翼臂的弧长比例 sv → (锚点, 所在骨序号, 下垂方向)。"""
        dist = sv * total
        j = min(2, max(k for k in range(3) if dist >= cum[k] - 1e-9))
        anchor = pts[j].lerp(pts[j + 1], min(1.0, (dist - cum[j]) / lens[j]))
        down = dirs[j].cross(nb).normalized()
        return anchor, j, (-down if down.z > 0 else down)

    def blade(name, sv, th_deg, L, W, lift, mat, sheath=0.0, veins=False, edge=True):
        anchor, j, down = station(sv)
        d = dirs[j]
        th = math.radians(th_deg)
        bd = (down * math.cos(th) + d * math.sin(th)).normalized()
        ya = d - bd * d.dot(bd)
        ya = ya.normalized() if ya.length > 1e-4 else nb.cross(bd).normalized()
        na = bd.cross(ya).normalized()
        origin = anchor + nb * lift - bd * 0.012 * s
        bulge = lambda x, y, L=L: 0.010 * s * math.sin(math.pi * x / L)
        outline = feather_outline(L, W)
        fe = plate(name, outline, 0.0050 * s, [mat], origin=origin, xaxis=bd, yaxis=ya, bulge=bulge)
        ctx.part(fe, rigid(bones[j]))
        if sheath:
            # 绯红羽根护套（比刃羽厚，正反两面都包住根部）+ V 形尖端的玫瑰金收口
            ctx.part(root_sheath(f"{name} sheath", outline, L, sheath, 0.0086 * s, M["lacquer"], origin, bd, ya,
                                 bulge), rigid(bones[j]))
            up_y, lo_y = feather_width(outline, sheath * L)
            tip = (sheath * L * 1.28, (up_y + lo_y) / 2 * 1.12)
            chevron = [(sheath * L, up_y * 1.12 + 0.0006 * s), tip, (sheath * L, lo_y * 1.12 - 0.0006 * s)]
            ctx.part(trim(f"{name} sheath rim", [origin + bd * x + ya * y + na * bulge(x, y) for x, y in chevron],
                          0.0050 * s, M["trim"], n=4), rigid(bones[j]))
        if veins:
            # 中线发光羽脉（贴着前缘偏上，避开护套）
            ctx.part(vein(f"{name} vein", origin, bd, ya, bulge, L, 0.02 * W, 0.060 * W, 0.0072 * s, M["vein"],
                          x0=max(0.30, sheath * 1.34)), rigid(bones[j]))
        if edge:
            # 前缘玫瑰金刃口：沿轮廓上沿走到尖端
            rim = [origin + bd * x + ya * (y + 0.0008 * s) + na * bulge(x, y) for x, y in outline[1:8:2]]
            ctx.part(trim(f"{name} edge", rim, 0.0029 * s, M["trim"], n=4), rigid(bones[j]))
        for f in (0.55, 1.0):
            clear.point(bones[j], origin + bd * L * f, f"wing{p}{label} feather")
    # 主刃羽：沿翼臂排布，根部下垂、越往翼尖越顺着翼臂外伸，逐片向后分层；
    # 象牙刃身 + 绯红羽根护套 + 玫瑰金前缘；外侧长羽加玫红羽脉
    N = cfg["blades"]
    for i in range(N):
        sv = lerp(0.10, 1.0, i / (N - 1))
        L = lerp(cfg["lmin"], cfg["lmax"], sv ** 0.9) * s * (1.06 if i == N - 1 else 1.0)
        blade(f"{ctx.title} feather {p}{label}{i}", sv, lerp(6, 80, sv ** 1.25), L,
              cfg["width"] * s * lerp(0.85, 1.0, sv), 0.006 * s + i * 0.0030 * s,
              M["ivory"], sheath=lerp(0.36, 0.24, sv), veins=sv > 0.40)
    # 覆羽：翼臂内侧一排短而宽的绯红刃，压住主刃羽的根部，玫瑰金前缘
    NC = cfg["coverts"]
    for i in range(NC):
        sv = lerp(0.05, 0.70, i / (NC - 1))
        blade(f"{ctx.title} covert {p}{label}{i}", sv, lerp(14, 52, sv), lerp(0.095, 0.180, sv) * s * cfg["cov"],
              0.050 * s, -0.009 * s - i * 0.0022 * s, M["lacquer"])
    return {"p": p, "side": side, "label": label, "pts": pts, "dirs": dirs, "n": n, "nb": nb, "bones": bones}


def build_blade(ctx, B, M):
    """展示页环绕用的花瓣刃（游戏内由原生飞剑绘制，不进 LOD）。"""
    s = B.s
    L, W = 0.46 * s, 0.105 * s
    bulge = lambda x, y: -0.028 * s * (y / (W * 0.5)) ** 2 * math.sin(math.pi * min(1.0, x / L) * 0.9 + 0.1)
    objs = [plate(f"{ctx.title} petal blade", petal_outline(L, W), 0.010 * s, [M["blade"]], origin=(0, 0, 0),
                  xaxis=(0, 1, 0), yaxis=(1, 0, 0), bulge=bulge, bev=0.0015 * s)]
    fuller = [(0.05 * L, 0.0), (0.2 * L, 0.035 * W), (0.78 * L, 0.012 * W), (0.84 * L, 0.0), (0.78 * L, -0.012 * W),
              (0.2 * L, -0.035 * W)]
    objs.append(plate(f"{ctx.title} petal fuller", fuller, 0.013 * s, [M["glow"]], origin=(0, 0, 0), xaxis=(0, 1, 0),
                      yaxis=(1, 0, 0), bulge=bulge))
    # 花瓣刃的法线为 -Z（xaxis=Y、yaxis=X），bulge 沿 -Z 偏移，叶脉贴在 +Z 一面
    for sd in (-1, 1):
        vein = []
        for t in [i / 12 for i in range(1, 13)]:
            x, y = t * L * 0.8 + 0.03 * L, sd * W * 0.22 * math.sin(math.pi * t ** 0.8)
            vein.append(Vector((y, x, -bulge(x, y) + 0.0058 * s)))
        objs.append(trim(f"{ctx.title} petal vein {sd}", vein, 0.0016 * s, M["hem"]))
    for k in range(3):
        a = (k - 1) * 0.9
        d = Vector((math.sin(a), -math.cos(a) * 0.6, 0)).normalized()
        sep = [(0, -0.008 * s), (0.03 * s, 0.012 * s), (0.075 * s, 0.0), (0.03 * s, -0.012 * s)]
        objs.append(plate(f"{ctx.title} petal sepal {k}", sep, 0.006 * s, [M["gilt"]], origin=(0, -0.005 * s, 0),
                          xaxis=d, yaxis=Vector((0, 0, 1)).cross(d), bev=0.001 * s))
    objs.append(tube(f"{ctx.title} petal grip", [(0, -0.01 * s, 0), (0, -0.075 * s, 0), (0, -0.13 * s, 0)],
                     [0.011 * s, 0.009 * s, 0.011 * s], [M["lacquer"]], n=10))
    objs.append(gem(f"{ctx.title} petal pommel", (0, -0.145 * s, 0), 0.014 * s, M["glow"], (1, 1.2, 1)))
    # 网页端按子网格的局部几何实例化环绕：顶点必须围绕局部原点、刃尖朝 +Y，所以合并时不做世界位移补偿
    blade = join(objs, f"{ctx.ID}_BLADE")
    blade.location = Vector((0.8, 0.05, 1.6)) * s
    ctx.hidden.append(blade)


# ===== 布料 =====
def cloth(B):
    s = B.s
    # 内裙：象牙符文丝，收窄下摆，细密竖褶
    under = Wrap("Under", "Pelvis", -math.pi + 0.004, math.pi - 0.004, top=B.z(1.262), bottom=B.z(-0.115),
                 r_top=(0.142 * s, 0.106 * s), r_bot=(0.275 * s, 0.245 * s), K=8, joints=J5, cy=0.004 * s,
                 flow=0.03 * s, flare_exp=1.35, folds=(13.0, 0.002 * s, 0.013 * s), seed=1.7, tails=20,
                 tail_len=(0.022 * s, 0.010 * s), curl=(0.008 * s, 0.003 * s))
    # 外袍：饱和绯红、前开襟露出内裙；上段贴身、下段才外扩（避免钟罩），深而纵向的垂褶 + 尼克斯式飘带尖角
    robe = Wrap("Robe", "Pelvis", 0.47, TAU - 0.47, top=B.z(1.272), bottom=B.z(0.24), r_top=(0.152 * s, 0.116 * s),
                r_bot=(0.420 * s, 0.360 * s), K=8, joints=J5, cy=0.004 * s, flow=0.08 * s, flare_exp=1.55,
                widen=0.03, folds=(11.0, 0.005 * s, 0.030 * s), seed=0.8, tails=10, tail_len=(0.24 * s, 0.10 * s),
                curl=(0.030 * s, 0.012 * s))

    def extent(z, u0, u1, layers, sign):
        best = 0.0
        for g in layers:
            for i in range(9):
                u = lerp(u0, u1, i / 8)
                top, bot = g.top(u), g.bottom(u)
                v = clamp((top - z) / max(1e-4, top - bot))
                best = max(best, sign * g.point(u, v).y)
        return best
    # 后垂饰：窄而收尖的象牙电路带（前片取消，正面让位给开襟与圣徽垂链）
    bt, bb = B.z(1.235), B.z(0.30)
    back = Panel("SashB", "Pelvis", bt, bb, [(0, 0.125 * s), (0.5, 0.110 * s), (1.0, 0.085 * s)],
                 lambda v: max(extent(lerp(bt, bb, v), 0.44, 0.56, [robe], -1),
                               extent(lerp(bt, bb, v), -0.06, 0.06, [under], -1)) + 0.026 * s,
                 side=-1, K=1, joints=J5, curve=1.0, point=0.22)
    return under, robe, back


def build(ctx):
    M = materials(ctx)
    B = Body(height=2.0, shoulder=0.205, bulk=1.0, chest=1.04, waist=0.92, limb=1.04, hover=0.25, female=True)
    s = B.s
    T = ctx.title
    clear = Clearance()
    suit_torso(ctx, B, M["suit"], nu=28, nv=22)
    for side, label in SIDES:
        suit_arm(ctx, B, side, label, M["suit"])
        suit_leg(ctx, B, side, label, M["suit"])
        hand(ctx, B, side, label, M["lacquer"], glow=M["glow"], scale=1.10)
        gauntlet_plate(ctx, B, side, label, M, 1.10)
    # 胸甲：高领口小 V、绯红漆甲、玫瑰金滚边（不细分、提高分段，省下细分带来的四倍面数）
    n0 = len(ctx.parts)
    cuirass_pt = shell(ctx, B, f"{T} cuirass", lambda a: B.z(1.668) - 0.014 * s * max(0.0, math.cos(a)) ** 6,
          lambda a: B.z(1.37) - 0.035 * s * max(0.0, math.cos(a)) ** 4, 0.011 * s, M["lacquer"],
          invdist(["Spine", "Chest"]), thick=0.007 * s, nu=80, nv=24, sub=0)
    cuirass = ctx.parts[n0][0]
    rims(ctx, cuirass_pt, f"{T} cuirass", 0.0034 * s, M["trim"], invdist(["Spine", "Chest"]), count=64,
         out=lambda p: Vector((p.x, p.y, 0)).normalized(), lift=0.0088 * s)
    # 胸甲中脊：圣杯牌下方一道玫瑰金棱线直落腰封
    keel = [B.on_torso(0, B.z(lerp(1.512, 1.338, i / 10)), 0.0205 * s) for i in range(11)]
    ctx.part(trim(f"{T} cuirass keel", keel, 0.0036 * s, M["trim"], n=6), invdist(["Spine", "Chest"]))
    # 玫瑰金雕花腰封：上沿藏进胸甲下缘，往下逐渐外扩成小裙腰（盖住外袍上沿），前片收尖
    def cinch_g(z):
        return 0.006 * s + 0.056 * s * smoothstep(B.z(1.345), B.z(1.232), z)
    cincher_pt = shell(ctx, B, f"{T} cincher", lambda a: B.z(1.40),
                       lambda a: B.z(1.232) - 0.050 * s * max(0.0, math.cos(a)) ** 3, 0.0, M["cincher"],
                       invdist(["Pelvis", "Spine"]), nu=64, nv=12, sub=0, thick=0.006 * s,
                       shape=lambda a, z: cinch_g(z))
    rims(ctx, cincher_pt, f"{T} cincher", 0.0032 * s, M["trim"], invdist(["Pelvis", "Spine"]), vs=(1.0,), count=60,
         out=lambda p: Vector((p.x, p.y, 0)).normalized(), lift=0.0080 * s)
    # 腰封正中的绯红交叉系带 + 玫瑰金扣眼
    for ph in (0, 1):
        lace = []
        for i in range(7):
            z = B.z(lerp(1.330, 1.262, i / 6))
            x = (0.022 if (i + ph) % 2 else -0.022) * s
            lace.append(B.on_torso(x, z, cinch_g(z) + 0.009 * s))
        ctx.part(trim(f"{T} cincher lace {ph}", lace, 0.0020 * s, M["lacquer"], n=5), invdist(["Pelvis", "Spine"]))
    for sd in (-1, 1):
        eyes = [B.on_torso(sd * 0.028 * s, z, cinch_g(z) + 0.008 * s)
                for z in [B.z(lerp(1.334, 1.258, i / 6)) for i in range(7)]]
        ctx.part(trim(f"{T} cincher seam {sd}", eyes, 0.0024 * s, M["trim"], n=5), invdist(["Pelvis", "Spine"]))
    zb = B.z(1.228)
    ctx.part(gem_lo(f"{T} cincher gem", B.on_torso(0, zb, cinch_g(zb) + 0.012 * s), 0.011 * s, M["glow"],
                  (0.9, 0.5, 1.25)), invdist(["Pelvis", "Spine"]))
    gorget2(ctx, B, M["ivory"], M["trim"], nu=32)
    build_chalice(ctx, B, M, cuirass)
    # 斜挎圣带：左肩斜下到右胯，绕开圣杯牌下沿；两枚玫瑰金圣徽扣
    stole(ctx, B, f"{T} stole", [(-0.128, 1.650), (-0.104, 1.575), (-0.060, 1.492), (0.012, 1.418),
                                 (0.086, 1.352), (0.132, 1.296), (0.150, 1.252)],
          0.050 * s, M["stole"], M["trim"], lambda z: max(0.021 * s, cinch_g(z) + 0.011 * s),
          invdist(["Pelvis", "Spine", "Chest"]), rep=4.0, medal=(M["gilt"], M["glow"]), medal_at=(0.40, 0.80))
    # 绯红分层肩甲：四片漆甲（第三片象牙）、玫瑰金滚边、顶片起脊并向上外挑出尖角，肩头宝石
    for side, label in SIDES:
        pauldron2(ctx, B, side, label, M["lacquer"], M["trim"], M["glow"], lames=4, radius=0.138, spread=1.34,
                  rise=1.18, tilt=0.30, spire=0.07, spire_at=0.05, spire_dir=(0.45, 0.0, 1.0),
                  theta=((0.04, 0.78), (0.50, 1.08), (0.84, 1.38), (1.14, 1.66)),
                  shrink=(1.0, 0.965, 0.935, 0.905), ridge=0.03, trim_r=0.0034, trim_n=24,
                  mats=[M["lacquer"], M["lacquer"], M["ivory"], M["lacquer"]], nu=32, nv=8)
        a = B.arms[label]
        rb = rerebrace(ctx, B, side, label, M["lacquer"], None, r=(0.066, 0.056), arc=1.9, nu=26, nv=8, sub=0)
        rims(ctx, rb, f"{T} rerebrace {label}", 0.0026 * s, M["trim"], rigid(f"UpperArm.{label}"), count=18,
             closed=False, out=axis_out(a["shoulder"], a["elbow"]), lift=0.0070 * s)
        vb = vambrace(ctx, B, side, label, M["lacquer"], None, inlay=M["inlay"], r=(0.052, 0.046), sub=0)
        rims(ctx, vb, f"{T} vambrace {label}", 0.0028 * s, M["trim"], rigid(f"Forearm.{label}"), count=20,
             out=axis_out(a["elbow"], a["wrist"]), lift=0.0065 * s)
        # 腕口玫瑰金内护腕：填住护臂喇叭口与细腕之间的空隙
        fd = (a["wrist"] - a["elbow"]).normalized()
        ctx.part(tube(f"{T} wrist cuff {label}", [a["wrist"] - fd * 0.070 * s, a["wrist"] - fd * 0.030 * s,
                                                a["wrist"] + fd * 0.004 * s],
                      [0.040 * s, 0.041 * s, 0.035 * s], [M["gilt"]], n=14), rigid(f"Forearm.{label}"))
        couter = a["elbow"] + Vector((side * 0.012 * s, -0.028 * s, 0))
        ctx.part(ellipsoid(f"{T} couter {label}", couter, (0.031 * s, 0.028 * s, 0.034 * s), [M["gilt"]], 14, 8),
                 rigid(("UpperArm." + label, 0.5), ("Forearm." + label, 0.5)))
        ctx.part(gem_lo(f"{T} couter gem {label}", couter + Vector((side * 0.018 * s, -0.020 * s, 0)), 0.0070 * s,
                      M["glow"], (1, 1, 1)), rigid(("UpperArm." + label, 0.5), ("Forearm." + label, 0.5)))
        # 垂腿藏在内裙里，只做一只尖头软靴（不做护胫，省面）
        L = B.legs[label]
        ctx.part(tube(f"{T} slipper {label}", [L["ankle"] + Vector((0, -0.045 * s, -0.02 * s)),
                                             L["ankle"] + Vector((0, 0.02 * s, -0.035 * s)), L["ball"], L["toe"]],
                      [0.040 * s, 0.044 * s, 0.036 * s, 0.0], [M["lacquer"]], n=12, fy=0.7),
                 chain([f"Foot.{label}", f"Toe.{label}"], f"Shin.{label}", 0.03))
    face = build_face(ctx, B, M)
    veil = build_veil(ctx, B, M)
    build_crown(ctx, B, M, face, veil)
    build_harness(ctx, B, M)
    wings = [build_wing(ctx, B, M, p, side, label, clear) for p in range(3) for side, label in SIDES]
    build_blade(ctx, B, M)
    under, robe, back = cloth(B)
    under.build(ctx, [M["silk"], M["lining"]], f"{T} underskirt", nu=76, nv=36, uv_scale=1.6)
    hem_line(ctx, under, f"{T} underskirt hem", 0.0024 * s, M["hem"], count=130, n=4)
    robe.build(ctx, [M["robe"], M["lining"]], f"{T} robe", nu=92, nv=44, uv_scale=1.6)
    cloth_edges(ctx, robe, f"{T} robe", 0.0036 * s, M["trim"], count=30, n=4)
    hem_line(ctx, robe, f"{T} robe hem", 0.0030 * s, M["hem"], count=160, n=4)
    back.build(ctx, [M["robe"], M["lining"]], f"{T} sash back", nu=10, nv=36, spine=(M["inlay"], 0.0019 * s))
    cloth_edges(ctx, back, f"{T} sash back", 0.0032 * s, M["trim"], count=24, n=4, top=True)
    # 短甲裙：腰封下一圈六片绯红盾形甲，玫瑰金滚边与中脊，顶端宝石；正前方留空露出开襟
    tassets(ctx, robe, f"{T} tasset", (0.84, 1.48, 2.14, -0.84, -1.48, -2.14), 0.31, B.z(1.262), 0.30 * s,
            M["lacquer"], M["trim"], M["glow"], margin=0.010 * s, flare=0.050 * s)
    # 腰间垂链：两道玫瑰金链自腰封两侧垂下，长链正中挂圣徽垂片与一串垂珠
    spec_u = garment(under)
    chain_links(ctx, f"{T} swag long", swag(under, -0.64, 0.64, B.z(1.240), B.z(1.080), 0.042 * s), M["gilt"], spec_u)
    chain_links(ctx, f"{T} swag short", swag(under, -0.42, 0.42, B.z(1.236), B.z(1.158), 0.048 * s, count=20),
                M["gilt"], spec_u)
    zc = B.z(1.005)
    c = wrap_base(under, 0.0, zc, 0.048 * s)
    top = wrap_base(under, 0.0, B.z(1.080), 0.044 * s)
    ctx.part(trim(f"{T} pendant hanger", [top, c + Vector((0, 0, 0.034 * s))], 0.0026 * s, M["gilt"], n=5), spec_u)
    sunburst(ctx, f"{T} pendant", c, M["gilt"], M["glow"], M["trim"], spec_u, r=0.034 * s)
    drop = [wrap_base(under, 0.0, B.z(0.935 - 0.020 * i), 0.046 * s) for i in range(7)]
    chain_links(ctx, f"{T} pendant tassel", drop, M["gilt"], spec_u, every=1)
    ctx.part(gem_lo(f"{T} pendant drop", drop[-1] - Vector((0, 0, 0.012 * s)), 0.010 * s, M["glow"], (0.8, 0.6, 1.5)),
             spec_u)
    # 身体胶囊体（翅膀穿插自检用）
    for side, label in SIDES:
        a = B.arms[label]
        clear.capsule(f"UpperArm.{label}", a["shoulder"], a["elbow"], 0.062 * s, f"upper arm {label}")
        clear.capsule(f"UpperArm.{label}", a["shoulder"] + Vector((0, 0, 0.02 * s)), a["shoulder"].lerp(a["elbow"], 0.25),
                      0.145 * s, f"pauldron {label}")
        clear.capsule(f"Forearm.{label}", a["elbow"], a["wrist"], 0.052 * s, f"forearm {label}")
        h = B.hands[label]
        clear.capsule(f"Hand.{label}", h["wrist"], h["knuckle"], 0.05 * s, f"hand {label}")
    clear.capsule("Chest", (0, 0, B.z(1.47)), (0, 0, B.z(1.66)), 0.135 * s, "chest")
    clear.capsule("Head", B.head_c - Vector((0, 0, 0.07 * s)), B.head_c + Vector((0, 0, 0.05 * s)), 0.125 * s, "head")
    clear.capsule("Pelvis", (0, 0, B.z(1.26)), (0, 0, B.z(0.95)), 0.21 * s, "robe top")
    return {"B": B, "under": under, "robe": robe, "back": back, "wings": wings, "clear": clear}


def skeleton(rig, st):
    B = st["B"]
    s = B.s
    add_skeleton(rig, B)
    hy = HARNESS_Y * s
    rig.bone("Wings", (0, hy, B.z(1.36)), (0, hy, B.z(1.58)), "Chest", roll=Y)
    for w in st["wings"]:
        for j in range(1, 4):
            rig.bone(w["bones"][j - 1], w["pts"][j - 1], w["pts"][j], "Wings" if j == 1 else w["bones"][j - 2],
                     roll=w["n"])
    for g in (st["under"], st["robe"], st["back"]):
        rig.add_garment(g)


# ===== 动作 =====
def wing_pose(pose, st, lift, sweep=None, bend=None, twist=None):
    """lift(p)：整翼绕抬翼轴上抬；sweep(p)：绕竖轴前扫（正值向前）；bend(p, j)：第 j 节相对上一节再抬（负值下垂）；
    twist(p)：首节绕自身轴的扭转（振翼时的羽面迎角）。"""
    for w in st["wings"]:
        p, side, n = w["p"], w["side"], w["n"]
        b1, b2, b3 = w["bones"]
        tw = twist(p) if twist else 0.0
        pose[b1] = R((w["dirs"][0], side * tw), (n, lift(p)), (Z, side * (sweep(p) if sweep else 0.0)))
        pose[b2] = R((n, bend(p, 2) if bend else 0.0))
        pose[b3] = R((n, bend(p, 3) if bend else 0.0))


def robes(rig, st, pose, flare, side=None, back=None):
    """三层布料同步摆动：内裙、外袍、后垂饰用同一组角度，层间距离保持不变。"""
    for g in (st["under"], st["robe"]):
        if back:
            rig.wind(pose, g, back, flare, side)
        else:
            rig.garment_pose(pose, g, flare, side)
    for g in (st["back"],):
        if back:
            rig.wind(pose, g, back, None, None)
        else:
            rig.garment_pose(pose, g, lambda k, j: flare(k, j) * 0.6)


def arms_rest(pose, B, t, lift=0.0):
    for label, sg in (("L", -1), ("R", 1)):
        pose[f"UpperArm.{label}"] = R((Y, sg * (0.16 + 0.03 * math.sin(t + 0.5 * sg))), (X, 0.12 + lift + 0.03 * math.sin(t + 1)))
        pose[f"Forearm.{label}"] = R((X, 0.42 + 0.04 * math.sin(t + 1.4)))
        pose[f"Hand.{label}"] = R((X, 0.06 * math.sin(2 * t + 0.3 * sg)))
        fingers(pose, B, label, lambda i: 0.10 + 0.06 * math.sin(2 * t + i * 0.6))


def idle_pose(rig, st, t):
    B = st["B"]
    s = B.s
    p = {"_hover": 0.030 * s * math.sin(t)}
    p["Pelvis"] = R((X, 0.02 * math.sin(t + 0.6)))
    p["Spine"] = R((X, -0.015 * math.sin(t + 1.0)))
    p["Chest"] = R((X, -0.02 * math.sin(t + 1.3)), (Y, 0.012 * math.sin(t)))
    p["Neck"] = R((X, 0.015 * math.sin(t + 2.0)))
    p["Head"] = R((X, -0.05 + 0.03 * math.sin(t + 2.2)), (Z, 0.04 * math.sin(t)))
    arms_rest(p, B, t)
    dangle2(B, t, p)
    wing_pose(p, st, lambda q: 0.03 + 0.06 * math.sin(t - 0.45 * q),
              bend=lambda q, j: 0.04 * math.sin(t - 0.45 * q - 0.7 * (j - 1)))
    robes(rig, st, p, lambda k, j: 0.03 + 0.03 * math.sin(t + k * 0.8 + j * 0.9),
          lambda k, j: 0.025 * math.sin(t + k * 0.9 + j * 0.6))
    return p


BEAT = (0.42, 0.36, 0.27)


def move_pose(rig, st, t):
    B = st["B"]
    s = B.s
    p = {"_hover": 0.020 * s + 0.035 * s * math.sin(t + 1.3)}      # 下扑时抬升
    p["Pelvis"] = R((X, -0.30 + 0.02 * math.sin(t)))
    p["Spine"] = R((X, -0.06))
    p["Chest"] = R((X, -0.02 + 0.03 * math.cos(t)))
    p["Neck"] = R((X, 0.16))
    p["Head"] = R((X, 0.20))
    for label, sg in (("L", -1), ("R", 1)):
        p[f"UpperArm.{label}"] = R((Y, sg * 0.02), (X, -0.40 + 0.05 * math.sin(t + 0.8)))
        p[f"Forearm.{label}"] = R((X, 0.22))
        p[f"Hand.{label}"] = R((X, -0.25 + 0.05 * math.sin(t)))
        fingers(p, B, label, lambda i: 0.08)
    dangle2(B, t, p, swing=0.05, bend=0.40, point=0.70, trail=0.20)
    wing_pose(p, st, lambda q: 0.08 + BEAT[q] * math.sin(t - 0.35 * q),
              sweep=lambda q: -0.08 + 0.08 * math.cos(t - 0.35 * q),
              bend=lambda q, j: BEAT[q] * 0.40 * math.sin(t - 0.35 * q - 0.85 * (j - 1)),
              twist=lambda q: 0.10 * math.cos(t - 0.35 * q))
    robes(rig, st, p, lambda k, j: 0.04 + 0.02 * math.sin(t + k * 0.7 + j),
          lambda k, j: 0.03 * math.sin(t + k * 0.6 + j * 0.8),
          back=lambda k, j: 0.14 + 0.05 * math.sin(t + k * 0.7 + j * 1.1))
    return p


def cast_key(rig, st, stage):
    """莲华新生：0 起势、1 合掌蓄力（群翼后收上扬）、2 双掌前推（群翼前扫）、3 定格。"""
    B = st["B"]
    s = B.s
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    if stage == 1:
        p["_hover"] = 0.05 * s
        p["Pelvis"] = R((X, 0.03))
        p["Chest"] = R((X, 0.08))
        p["Head"] = R((X, -0.10))
        for label, sd in (("L", -1), ("R", 1)):
            rig.aim(p, f"UpperArm.{label}", (sd * 0.35, 0.40, -0.85))
            rig.aim(p, f"Forearm.{label}", (-sd * 0.55, 0.70, 0.45))
            h = B.hands[label]
            rig.aim(p, f"Hand.{label}", (-sd * 0.35, 0.75, 0.35), up=(sd * -0.3, -0.2, 1.0), rest_up=h["n"])
            fingers(p, B, label, lambda i: 0.30)
        wing_pose(p, st, lambda q: 0.28, sweep=lambda q: -0.28, bend=lambda q, j: 0.06)
        robes(rig, st, p, lambda k, j: 0.05)
    else:
        follow = stage == 3
        p["_hover"] = (0.03 if follow else 0.02) * s
        p["Pelvis"] = R((X, -0.10))
        p["Spine"] = R((X, -0.05))
        p["Chest"] = R((X, -0.04))
        p["Head"] = R((X, 0.06))
        for label, sd in (("L", -1), ("R", 1)):
            spread = 0.30 if follow else 0.18
            rig.aim(p, f"UpperArm.{label}", (sd * spread, 0.95, 0.02 if follow else 0.08))
            rig.aim(p, f"Forearm.{label}", (sd * (spread * 0.6), 1.0, 0.08))
            h = B.hands[label]
            rig.aim(p, f"Hand.{label}", (sd * 0.15, 0.30, 1.0), up=(0, 1, -0.1), rest_up=h["n"])
            fingers(p, B, label, lambda i: -0.10, 0.5)
        sweep = 0.40 if follow else 0.52
        wing_pose(p, st, lambda q: 0.10 - 0.04 * q, sweep=lambda q: sweep * (0.75 if q == 0 else 1.0),
                  bend=lambda q, j: -0.10, twist=lambda q: 0.12)
        robes(rig, st, p, lambda k, j: 0.06, back=lambda k, j: 0.08)
    return p


def channel_key(rig, st, stage):
    """刃花绽放：双臂向上张开，三对翼全展高举，长袍被气流托起。"""
    B = st["B"]
    s = B.s
    p = idle_pose(rig, st, 0)
    if stage == 0:
        return p
    p["_hover"] = 0.14 * s
    p["Pelvis"] = R((X, 0.04))
    p["Chest"] = R((X, 0.10))
    p["Neck"] = R((X, 0.08))
    p["Head"] = R((X, 0.18))
    for label, sd in (("L", -1), ("R", 1)):
        rig.aim(p, f"UpperArm.{label}", (sd * 0.62, 0.18, 0.76))
        rig.aim(p, f"Forearm.{label}", (sd * 0.48, 0.24, 0.85))
        h = B.hands[label]
        rig.aim(p, f"Hand.{label}", (sd * 0.35, 0.25, 0.92), up=(sd * 0.3, 1.0, 0.2), rest_up=h["n"])
        fingers(p, B, label, lambda i: -0.12, 0.7)
    dangle2(B, 0, p, swing=0.0, bend=0.12, point=0.80)
    wing_pose(p, st, lambda q: (0.55, 0.46, 0.36)[q], sweep=lambda q: -0.14, bend=lambda q, j: 0.14)
    robes(rig, st, p, lambda k, j: 0.13)
    return p


def animate(rig, st):
    rig.loop("Idle", 72, lambda t: idle_pose(rig, st, t))
    rig.loop("Move", 24, lambda t: move_pose(rig, st, t), step=1)
    k = [cast_key(rig, st, i) for i in range(4)]
    cast = [(1, k[0]), (8, k[1]), (14, k[2]), (20, k[3]), (32, k[0])]
    rig.keyed("Cast", cast)
    c = [channel_key(rig, st, i) for i in range(2)]
    channel = [(1, c[0]), (13, c[1]), (28, c[1]), (42, c[0])]
    rig.keyed("Channel", channel)
    clear = st["clear"]
    clear.report(rig, "Idle", [idle_pose(rig, st, TAU * i / 24) for i in range(24)])
    clear.report(rig, "Move", [move_pose(rig, st, TAU * i / 24) for i in range(24)])
    clear.report(rig, "Cast", keyed_samples(cast))
    clear.report(rig, "Channel", keyed_samples(channel))
