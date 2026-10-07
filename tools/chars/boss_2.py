"""Boss 2 · 钢铁巨兽 · 攻城原型（Iron Behemoth · Siege Prototype）· 第二轮返工。

设定：近 9 m 长、船体离地 2.1 m、含炮塔近 6 m 高的四足攻城兽，整体宽腿重心稳。蓝钢铆接船体外覆七道瓦叠铁甲
（三块拼板、黄铜包边与铆钉排、脊背排气鳍），船体两侧有带浮雕齿轮徽记与舷窗的侧甲，四个高耸的三层肩 / 髋叠甲
（顶端尖刺、琥珀灯）；背上一座棱面炮塔（前弧护盾板、环形装饰尖刺、旗杆与天线组）与一门带后坐的攻城炮；
头后立扇形颈盾（浮雕齿轮、后掠刺），楔形撞角龙首（五层前倾叠甲、黄铜撞头带刻纹与铆钉、前向眼匣里的斜向琥珀
眼缝、可开合的格栅颚、分节锤角）；两侧黄铜 / 紫铜管路串起发光琥珀仪表；胸下悬挂锅炉舱与熔炉门；后背两座烟囱、
肩部两个排气口（喷口只做烧红的喷口环 + 薄片状半透明火舌，大火留给游戏内特效）；四条粗壮的“反关节”机械腿
（双组液压缸、铰接护胫、爪状蹄甲），侧面挂铰接裙甲；尾端铁锤。
动作：Idle（锅炉呼吸、炮塔巡视）/ Move（四拍步态，逐腿 IK + 自建脚相位轨道）/ Attack（后缩蓄力 → 冲锋撞角 →
上挑）/ Enrage（后腿人立、前蹄刨空、炮口朝天连发两炮、所有排气口爆燃，落地砸地）。

网页端要驱动的节点：BOSS_2_TURRET（炮塔：座圈 + 塔身 + 护盾 + 旗杆全在内，随 Turret 骨）、BOSS_2_CANNON（炮管，
随 Barrel 骨后坐）、BOSS_2_MUZZLE（炮口焰，Muzzle 骨缩放）；Stack.L/R、Vent.L/R 骨缩放控制喷口火舌。

私有模块：_b2r2_parts.py（半透明火舌、齿轮徽记、壳片、面数统计）、_b2r2_shots.py（紧凑取景的审图渲染：
最终的 front / three-quarter / rear / side / top / game / detail 及动作帧由它出图，见该文件头部用法）。
"""

import math
import sys

from mathutils import Matrix, Vector

from kit.core import (TAU, auto_smooth, clamp, filigree_maps, finish, fn, gem, join, lathe, lerp, loft, orient, plate,
                      rigid, ring_points, smoothstep, spike, surface, tube)
from kit.core import trim as _trim
from kit.rig import R, X, Y, Z

from chars._bossA_common import (blob, bbox_report, dial_maps, ease_io, hermite, interval_weights, loop,
                                 magma_maps, panel_maps, register_chains, sampled, seam_check, shards, sweep,
                                 track, with_defaults)
from chars._bossA_common import studs as _studs
from chars import _b2r2_parts as P2

TITLE = "Iron Behemoth"
ACCENT = (0.92, 0.76, 0.55)
CLIPS = ("Idle", "Move", "Attack", "Enrage")
GAME_TRIS = 86000
LOD_KEEP = ("glow", "core", "flame", "dial")
REVIEW_POSE = ("Idle", 1)
AMBER = (1.0, 0.58, 0.16)
SIDES = ((-1, "L"), (1, "R"))
ZB = 0.30              # 上身整体抬高量：躯干、头、炮塔、烟囱、尾、裙甲先按 0 基准造完再整体上移，腿按最终坐标另造（腿加长）


def V(x, y, z):
    return Vector((x, y, z))


def trim(name, points, radius, mat, closed=False, n=None, per=1):
    """滚边：细管（半径 ≤ 0.026 用 4 边，其余 5 边）——滚边是全身最费面的一类，截面够用就行。"""
    return _trim(name, points, radius, mat, closed=closed, n=4 if radius <= 0.026 else 5, per=per)


def studs(name, items, mats, seg=6, rings=2, dome=0.55):
    """铆钉：默认 6 边 2 圈（18 面一颗）；半径 ≥ 0.04 的大钉用 3 圈。"""
    big = max(it[2] for it in items) >= 0.04 if items else False
    return _studs(name, items, mats, seg=seg + (2 if big else 0), rings=3 if big else rings, dome=dome)


# ===== 材质 =====
def materials(ctx):
    M = ctx.M
    ctx.mat("plate", "blued riveted hull", (0.22, 0.26, 0.34), metal=0.78, rough=0.30, coat=0.3)
    ctx.texture("plate", panel_maps((0.23, 0.27, 0.36), (0.03, 0.035, 0.045), (0.66, 0.50, 0.26), size=1024, cols=3,
                                    rows=3, seed=8), normal_strength=0.7)
    ctx.mat("iron", "blackened siege iron", (0.14, 0.13, 0.125), metal=0.8, rough=0.36, coat=0.2)
    ctx.texture("iron", filigree_maps((0.15, 0.14, 0.135), (0.27, 0.22, 0.16), size=1024, seed=21, density=22,
                                      width=1), normal_strength=0.45)
    ctx.mat("brass", "engraved brass", (0.80, 0.58, 0.30), metal=1.0, rough=0.24)
    ctx.texture("brass", filigree_maps((0.80, 0.58, 0.30), (0.36, 0.22, 0.09), size=1024, seed=5, density=20, width=1),
                normal_strength=0.5)
    ctx.mat("trim", "polished brass trim", (0.90, 0.68, 0.36), metal=1.0, rough=0.18)
    ctx.mat("copper", "copper pipe", (0.74, 0.38, 0.22), metal=1.0, rough=0.28)
    ctx.mat("steel", "piston chrome", (0.82, 0.82, 0.84), metal=1.0, rough=0.10)
    ctx.mat("dark", "oiled gunmetal", (0.035, 0.035, 0.04), metal=0.9, rough=0.42)
    ctx.mat("horn", "bronze ram horn", (0.30, 0.20, 0.11), metal=0.85, rough=0.34, coat=0.2)
    # 发光件：AgX 会把高强度橙色压成奶白，所以色相压深（偏红橙）、强度收在 2.5~3.5，保住“琥珀火光”的饱和度
    ctx.mat("glow", "amber gauge glow", (0.9, 0.30, 0.04), emit=(1.0, 0.34, 0.04), strength=1.5)
    ctx.mat("core", "furnace core glow", (0.9, 0.28, 0.04), emit=(1.0, 0.30, 0.03), strength=3.2)
    ctx.mat("dial", "gauge dial face", (0.9, 0.55, 0.2), emit=AMBER, strength=1.8)
    ctx.texture("dial", dial_maps((1.0, 0.56, 0.14), size=256), emit_strength=1.9)
    ctx.mat("furnace", "furnace firebox", (0.5, 0.12, 0.02), emit=(1.0, 0.34, 0.05), strength=3.0)
    ctx.texture("furnace", magma_maps((1.0, 0.50, 0.12), base_rgb=(0.30, 0.07, 0.01), size=512, seed=4, cells=4,
                                      width=0.08, fine=0.3, heat=1.0, hot=0.6), emit_strength=3.4, normal_strength=0.3)
    # 火焰：不再用实心锥体。两层半透明薄片材质（RGBA 贴图：外焰深红橙、内焰黄白），alpha 向尖端 / 边缘渐隐
    M["flame"] = P2.flame_material(f"{ctx.title} vent blast flame", P2.flame_maps(128, seed=3), 2.4)
    M["flamehot"] = P2.flame_material(f"{ctx.title} vent blast flame core",
                                      P2.flame_maps(128, seed=9, core=1.7, edge=(1.0, 0.45, 0.08), mid=(1.0, 0.74, 0.30),
                                                    hot=(1.0, 0.96, 0.78)), 3.2)
    return M


# ===== 船体（躯干）=====
# (y, 半宽, 半高, 中心高)：臀端收圆 → 髋 → 腰 → 肩峰隆起 → 胸前收口；离地 1.8 m，肩峰高于髋
HULL = [(-3.05, 0.14, 0.14, 2.62), (-2.95, 0.62, 0.50, 2.64), (-2.55, 1.05, 0.78, 2.68), (-1.85, 1.30, 0.92, 2.70),
        (-0.80, 1.20, 0.82, 2.62), (0.30, 1.30, 0.92, 2.70), (1.30, 1.52, 1.10, 2.80), (2.05, 1.30, 0.98, 2.70),
        (2.50, 0.88, 0.74, 2.55), (2.70, 0.26, 0.28, 2.45)]
HP = 3.2              # 截面超椭圆指数：更方正的“坦克船体”，不是圆胖的香肠
TORSO_BOUNDS = [("Rump", -9.0, -0.5), ("Spine", -0.5, 1.0), ("Chest", 1.0, 9.0)]


def hull(y, a, grow=0.0):
    """船体表面点：a=0 正上方，增大转向 +X，π 为腹底；grow 为向外加厚（米）。"""
    w, h, c = hermite(HULL, y)
    s, co = math.sin(a), math.cos(a)
    e = 2.0 / HP
    return Vector(((w + grow) * math.copysign(abs(s) ** e, s), y, c + (h + grow) * math.copysign(abs(co) ** e, co)))


def hull_n(y, a):
    """船体外法向（保证朝外）。"""
    da = hull(y, a + 0.01) - hull(y, a - 0.01)
    dy = hull(y + 0.01, a) - hull(y - 0.01, a)
    n = da.cross(dy).normalized()
    ctr = Vector((0, y, hermite(HULL, y)[2]))
    return n if n.dot(hull(y, a) - ctr) > 0 else -n


def hull_ref(c):
    return Vector((0, c.y, hermite(HULL, c.y)[2]))


def torso_w(p):
    return interval_weights(p.y, TORSO_BOUNDS, 0.35)


def torso_bone(y):
    return "Rump" if y < -0.5 else ("Spine" if y < 1.0 else "Chest")


def hull_plate(ctx, M, name, y0, y1, a0, a1, g0, g1, mat="iron", th=0.045, nu=14, nv=8, uv=(2.0, 1.0), spec=None):
    """贴合船体的一块厚甲片：y0→y1（v）、a0→a1（u）、外推量 g0→g1。返回 (对象, 取点函数)。"""
    def pt(u, v):
        return hull(lerp(y0, y1, v), lerp(a0, a1, u), lerp(g0, g1, v))
    obj = surface(name, pt, nu, nv, [M[mat]], uvfn=lambda u, v: (u * uv[0], v * uv[1]))
    orient(obj, hull_ref)
    ctx.part(finish(obj, th, -1, 0), spec or fn(torso_w))
    return pt


def build_hull(ctx, M):
    T = ctx.title
    y0, y1 = HULL[0][0], HULL[-1][0]
    obj = surface(f"{T} hull", lambda u, v: hull(lerp(y1, y0, v), u * TAU), 56, 72, [M["plate"]],
                  closed_u=True, uvfn=lambda u, v: (u * 5, v * 4.6))
    orient(obj, hull_ref)
    ctx.part(obj, fn(torso_w))
    # 腹底加强肋（深色铁箍）
    for y in (-1.5, -0.9, -0.3, 0.3, 0.9, 1.5):
        pts = [hull(y, a, 0.02) for a in [math.pi + (q / 14 - 0.5) * 2.4 for q in range(15)]]
        ctx.part(trim(f"{T} belly rib {y:.1f}", pts, 0.05, M["dark"]), fn(torso_w))


def build_carapace(ctx, M):
    """七道瓦叠背甲：每道三块拼板（中块略高，边块略低，拼缝处黄铜压条 + 铆钉），前片后缘压住后片前缘；
    后缘黄铜包边、前缘铆钉排、琥珀散热槽（只开中段）；排气鳍在炮塔前后。"""
    T = ctx.title
    A, AC = 1.36, 0.52
    for k in range(7):
        y0 = 2.20 - k * 0.72
        y1 = y0 - 0.86
        mid_y = lerp(y0, y1, 0.55)
        plates = [(-AC, AC, 0.0), (AC, A, -0.030), (-A, -AC, -0.030)]
        for pi, (a0, a1, dg) in enumerate(plates):
            g0, g1 = 0.062 + dg, 0.140 + dg
            hull_plate(ctx, M, f"{T} carapace {k}.{pi}", y0, y1, a0, a1, g0, g1, "iron", 0.05,
                       nu=12 if pi == 0 else 8, nv=8, uv=(1.3, 0.8))
            rim = [hull(y1, lerp(a0, a1, i / 12), g1 + 0.014) for i in range(13)]
            ctx.part(trim(f"{T} carapace rim {k}.{pi}", rim, 0.032, M["trim"]), fn(torso_w))
            items = [(hull(y0 - 0.07, lerp(a0, a1, (i + 0.5) / 6), g0 + 0.026), hull_n(y0 - 0.07, lerp(a0, a1, (i + 0.5) / 6)),
                      0.032) for i in range(6 if pi == 0 else 4)]
            ctx.part(studs(f"{T} carapace rivets {k}.{pi}", items, [M["trim"]]), fn(torso_w))
        # 拼缝压条
        for a in (-AC, AC):
            seam = [hull(lerp(y0, y1, i / 6), a, 0.062 + 0.078 * i / 6 + 0.02) for i in range(7)]
            ctx.part(trim(f"{T} carapace seam {k}{a:+.1f}", seam, 0.022, M["trim"]), fn(torso_w))
        # 散热槽：后缘包边前方一道发光槽（只开中段）
        g = 0.14 - 0.062 * 0.10 / 0.86 + 0.006
        slot = [hull(y1 + 0.10, lerp(-0.9, 0.9, i / 24), g) for i in range(25)]
        ctx.part(trim(f"{T} carapace heat seam {k}", slot, 0.026, M["core"]), fn(torso_w))
        for sd in (-1, 1):
            side = [hull(lerp(y0, y1, i / 6), sd * A, 0.058 + 0.078 * i / 6 + 0.012) for i in range(7)]
            ctx.part(trim(f"{T} carapace edge {k}{sd}", side, 0.024, M["trim"]), fn(torso_w))
        # 排气鳍：炮塔前后各几片（后掠的薄刃，黄铜前缘 + 琥珀散热缝）
        if k in (0, 1, 5, 6):
            height = (1.10, 1.00, 0.92, 0.74)[(0, 1, 5, 6).index(k)]
            fin_blade(ctx, M, hull(mid_y, 0.0, 0.17), hull_n(mid_y, 0.0), height, 0.36, torso_bone(mid_y), f"{k}")
        if k in (0, 1, 5, 6):
            for sd in (-1, 1):
                b2 = hull(mid_y, sd * 0.78, 0.16)
                nrm = hull_n(mid_y, sd * 0.78)
                ctx.part(spike(f"{T} flank spike {k}{sd}", b2, b2 + nrm * 0.26 + V(0, -0.14, 0.10), 0.075, [M["trim"]],
                               sides=5), fn(torso_w))


def fin_blade(ctx, M, base, nrm, h, L, bone, tag):
    """后掠排气鳍：在 (向后, 向上) 平面里的薄刃，厚 0.05。"""
    T = ctx.title
    up = Vector(nrm).normalized()
    outline = [(-L * 0.9, 0.0), (L * 1.1, 0.0), (L * 0.55, h * 0.55), (L * 0.18, h), (-L * 0.20, h * 0.72), (-L * 0.62, h * 0.30)]
    base = Vector(base) - up * 0.04
    ctx.part(plate(f"{T} dorsal fin {tag}", outline, 0.05, [M["plate"]], origin=base, xaxis=(0, -1, 0), yaxis=up,
                   bev=0.008), rigid(bone))
    edge = [base + V(0, -1, 0) * (x + 0.012) + up * (y + 0.012) for x, y in
            [(-L * 0.62, h * 0.30), (-L * 0.20, h * 0.72), (L * 0.18, h), (L * 0.55, h * 0.55)]]
    ctx.part(trim(f"{T} dorsal fin edge {tag}", edge, 0.020, M["trim"]), rigid(bone))
    slot = [(-L * 0.12, h * 0.12), (L * 0.46, h * 0.12), (L * 0.40, h * 0.20), (-L * 0.08, h * 0.20)]
    for sd in (-1, 1):
        ctx.part(plate(f"{T} dorsal fin slot {tag}{sd}", slot, 0.012, [M["core"]], origin=base + V(sd * 0.030, 0, 0),
                       xaxis=(0, -1, 0), yaxis=up), rigid(bone))


def build_flank(ctx, M):
    """侧甲：船体两侧 a=1.56~2.02 的大块贴合装甲板（三格 + 黄铜滚边 + 铆钉）+ 浮雕齿轮徽记。"""
    T = ctx.title
    y0, y1 = 0.72, -1.50
    for sd, s in SIDES:
        a0, a1 = sd * 1.56, sd * 2.02
        hull_plate(ctx, M, f"{T} flank panel {s}", y0, y1, a0, a1, 0.056, 0.056, "plate", 0.05, nu=10, nv=22,
                   uv=(0.8, 2.4))
        g = 0.092
        for a in (a0, a1):
            ctx.part(trim(f"{T} flank edge {s}{a:.2f}", [hull(lerp(y0, y1, i / 18), a, g) for i in range(19)], 0.030,
                          M["trim"]), fn(torso_w))
        for y in (y0, y1, -0.20, -0.85):
            ctx.part(trim(f"{T} flank rib {s}{y:.2f}", [hull(y, lerp(a0, a1, i / 8), g) for i in range(9)], 0.026,
                          M["trim"]), fn(torso_w))
        items = []
        for a in (a0, a1):
            for i in range(10):
                y = lerp(y0 - 0.08, y1 + 0.08, i / 9)
                items.append((hull(y, a, g + 0.012), hull_n(y, a), 0.036))
        ctx.part(studs(f"{T} flank rivets {s}", items, [M["brass"]]), fn(torso_w))
        for yp in (0.26, -1.18):                    # 锅炉观火舷窗：黄铜圈 + 琥珀玻璃 + 螺栓
            ap = lerp(a0, a1, 0.5)
            porthole(ctx, M, hull(yp, ap, 0.07), hull_n(yp, ap), 0.17, fn(torso_w), f"{s}{yp:+.2f}")
        yc, ac = -0.52, lerp(a0, a1, 0.5)
        for o in P2.emblem(f"{T} flank emblem {s}", hull(yc, ac, 0.07), hull_n(yc, ac), 0.34,
                           dict(gear=M["brass"], disc=M["dark"], hub=M["glow"], trim=M["trim"], spoke=M["brass"]),
                           teeth=14, depth=0.06, hub=M["glow"], spokes=6):
            ctx.part(o, fn(torso_w))


def porthole(ctx, M, c, nrm, r, spec, tag):
    """舷窗：黄铜厚圈 + 内圈暗环 + 琥珀发光玻璃 + 一圈螺栓。"""
    T = ctx.title
    n = Vector(nrm).normalized()
    a = n.orthogonal().normalized()
    b = n.cross(a)
    ctx.part(trim(f"{T} porthole ring {tag}", ring_points(c + n * 0.03, n, r, 20), 0.040, M["trim"], closed=True), spec)
    ctx.part(trim(f"{T} porthole inner {tag}", ring_points(c + n * 0.03, n, r * 0.74, 18), 0.026, M["dark"], closed=True), spec)
    glass = [(math.cos(q / 16 * TAU) * r * 0.70, math.sin(q / 16 * TAU) * r * 0.70) for q in range(16)]
    ctx.part(plate(f"{T} porthole glass {tag}", glass, 0.02, [M["glow"]], origin=c + n * 0.028, xaxis=a, yaxis=b), spec)
    items = [(c + n * 0.03 + (a * math.cos(q / 8 * TAU) + b * math.sin(q / 8 * TAU)) * r * 1.22,
              n, 0.024) for q in range(8)]
    ctx.part(studs(f"{T} porthole bolts {tag}", items, [M["brass"]]), spec)


# ===== 肩胛 / 髋部叠甲 =====
def build_pauldrons(ctx, M, legs):
    """每条腿根上方三层椭球壳片逐层抬高、缩小的高耸叠甲：黄铜唇边 + 铆钉 + 顶端尖刺 + 琥珀灯。"""
    T = ctx.title
    for (leg, s), L in legs.items():
        sd = L["sd"]
        k = 1.0 if leg == "Fore" else 0.88
        P0 = V(sd * (1.22 if leg == "Fore" else 1.16), L["top"].y, (3.05 if leg == "Fore" else 3.0) + ZB)
        spec = rigid(L["parent"])
        for i in range(3):
            rx, ry, rz = (1.20 - 0.22 * i) * k, (0.92 - 0.18 * i) * k, (0.80 - 0.12 * i) * k
            Pi = P0 + V(sd * 0.05 * i, 0, 0.30 * i * k)
            lame, f = P2.dome_lame(f"{T} {leg} pauldron {s}{i}", Pi, sd, rx, ry, rz, 0.0, 1.50, [M["plate"]], nu=18, nv=8)
            orient(lame, lambda c, Pi=Pi: Pi)
            ctx.part(finish(lame, 0.05, -1, 0), spec)
            lip = [f(q / 20, 0.0) + V(sd * 0.012, 0, 0.012) for q in range(21)]
            ctx.part(trim(f"{T} {leg} pauldron lip {s}{i}", lip, 0.036, M["trim"], n=6), spec)
            items = []
            for q in range(1, 9):
                p = f(q / 9, 0.07)
                items.append((p, (p - Pi).normalized(), 0.038))
            ctx.part(studs(f"{T} {leg} pauldron rivets {s}{i}", items, [M["brass"]]), spec)
            # 层间滚边：压在壳面中部的一道黄铜细环
            mid = [f(q / 20, 0.52) + (f(q / 20, 0.52) - Pi).normalized() * 0.012 for q in range(1, 20)]
            ctx.part(trim(f"{T} {leg} pauldron band {s}{i}", mid, 0.02, M["trim"], n=5), spec)
            apex = f(0.5, 1.0)
            ctx.part(spike(f"{T} {leg} pauldron spike {s}{i}", apex - V(0, 0, 0.04), apex + V(sd * 0.10, 0, (0.46 - 0.10 * i) * k),
                           (0.12 - 0.02 * i) * k, [M["trim"] if i == 2 else M["iron"]], sides=7), spec)
        lamp = P2.dome_point(P0, sd, 1.20 * k, 0.92 * k, 0.80 * k, 0.04, -0.62)
        ctx.part(gem(f"{T} {leg} pauldron lamp {s}", lamp + V(sd * 0.03, 0, 0.0), 0.07, M["glow"], (1, 1, 1)), spec)


# ===== 管路与仪表 =====
def gauge(ctx, M, c, nrm, spec, tag, r=0.17, needle=0.0):
    """圆形仪表：黄铜表壳 + 发光表盘（刻度贴图）+ 包边 + 指针；spec=None 时只返回对象（给炮塔节点合并用）。"""
    T = ctx.title
    n = Vector(nrm).normalized()
    a = n.orthogonal().normalized()
    b = n.cross(a)
    objs = [sweep(f"{T} gauge case {tag}", [c - n * 0.10, c + n * 0.05], [r * 1.05, r * 1.02], [M["brass"]], n=16, per=1)]
    outline = [(math.cos(q / 24 * TAU) * r * 0.9, math.sin(q / 24 * TAU) * r * 0.9) for q in range(24)]
    objs.append(plate(f"{T} gauge face {tag}", outline, 0.012, [M["dial"]], origin=c + n * 0.052, xaxis=a, yaxis=b))
    objs.append(trim(f"{T} gauge bezel {tag}", ring_points(c + n * 0.06, n, r * 0.97, 24), 0.022, M["trim"], closed=True))
    d = a * math.cos(needle) + b * math.sin(needle)
    objs.append(tube(f"{T} gauge needle {tag}", [c + n * 0.07 - d * r * 0.15, c + n * 0.07 + d * r * 0.75],
                     [0.012, 0.006], [M["dark"]], n=4))
    if spec is not None:
        for o in objs:
            ctx.part(o, spec)
    return objs


def build_pipes(ctx, M):
    """两侧黄铜主管（接到烟囱）+ 紫铜副管 + 法兰 + 琥珀仪表 + 阀轮。"""
    T = ctx.title
    for sd, label in SIDES:
        ys = [2.05 - i * 0.52 for i in range(9)]
        main = [hull(y, sd * 1.50, 0.15) for y in ys] + [V(sd * 0.86, -2.30, 3.40), V(sd * 0.64, -2.30, 3.62)]
        ctx.part(sweep(f"{T} brass pipe {label}", main, [0.085] * len(main), [M["trim"]], n=10, per=3), fn(torso_w))
        for y in (1.65, 0.45, -0.75, -1.95):
            c = hull(y, sd * 1.50, 0.15)
            ctx.part(trim(f"{T} flange {label}{y:.1f}", ring_points(c, (0, 1, 0), 0.12, 12), 0.032, M["brass"],
                          closed=True), rigid(torso_bone(y)))
        low = [hull(y, sd * 1.62, 0.13) for y in [1.85 - i * 0.55 for i in range(7)]]
        ctx.part(sweep(f"{T} copper pipe {label}", low, [0.06] * len(low), [M["copper"]], n=8, per=3), fn(torso_w))
        for y in (0.95, -1.35):
            gauge(ctx, M, hull(y, sd * 1.36, 0.24), hull_n(y, sd * 1.36), rigid(torso_bone(y)), f"{label}{y:.1f}", 0.19,
                  needle=0.6 + y)
        # 阀轮
        c = hull(0.35, sd * 1.40, 0.26)
        nrm = hull_n(0.35, sd * 1.40)
        ctx.part(trim(f"{T} valve wheel {label}", ring_points(c, nrm, 0.14, 16), 0.022, M["brass"], closed=True),
                 rigid("Spine"))
        a0 = nrm.orthogonal().normalized()
        b0 = nrm.cross(a0)
        for q in range(3):
            d = a0 * math.cos(q / 3 * TAU) + b0 * math.sin(q / 3 * TAU)
            ctx.part(tube(f"{T} valve spoke {label}{q}", [c - d * 0.14, c + d * 0.14], [0.014, 0.014], [M["brass"]], n=5),
                     rigid("Spine"))
        ctx.part(gem(f"{T} valve hub {label}", c, 0.04, M["glow"], (1, 1, 1)), rigid("Spine"))


def build_furnace(ctx, M):
    """胸前熔炉门：胸下悬挂的锅炉舱（黑铁壳 + 两道黄铜箍）+ 外凸的火箱 + 黄铜门框与栅条 + 上方铁檐 + 门两侧齿轮铭牌。
    头抬高后门露在下颌之下，低机位正面可见。"""
    T = ctx.title
    c = V(0, 2.84, 1.56)
    hw, hh = 0.62, 0.30
    tilt = V(0, -0.30, 0.954)                          # 门面略朝下，低机位正面看得到
    ctx.part(blob(f"{T} boiler pod", V(0, 2.30, 1.70), (0.88, 0.62, 0.42), [M["iron"]], 28, 14, power=3.0, tile=0.8), rigid("Chest"))
    for y in (2.10, 2.50):
        ctx.part(trim(f"{T} boiler band {y}", ring_points(V(0, y, 1.70), (0, 1, 0), 0.43, 24), 0.04, M["trim"], closed=True),
                 rigid("Chest"))
    outline = []
    for q in range(28):
        t = q / 28 * TAU
        cx, cy = math.cos(t), math.sin(t)
        outline.append((hw * math.copysign(abs(cx) ** 0.35, cx), hh * math.copysign(abs(cy) ** 0.35, cy)))
    ctx.part(plate(f"{T} firebox", outline, 0.16, [M["furnace"]], origin=c, xaxis=(1, 0, 0), yaxis=tilt), rigid("Chest"))
    nrm = V(1, 0, 0).cross(tilt)
    frame = [c + V(x * 1.07, 0, 0) + tilt * (y * 1.09) + nrm * 0.09 for x, y in outline]
    ctx.part(trim(f"{T} firebox frame", frame, 0.045, M["trim"], closed=True), rigid("Chest"))
    frame2 = [c + V(x * 1.20, 0, 0) + tilt * (y * 1.26) + nrm * 0.05 for x, y in outline]
    ctx.part(trim(f"{T} firebox frame outer", frame2, 0.032, M["brass"], closed=True), rigid("Chest"))
    for i in range(5):
        x = (i - 2) / 2 * hw * 0.8
        ctx.part(tube(f"{T} firebox bar {i}", [c + V(x, 0, 0) + tilt * (-hh * 0.95) + nrm * 0.10, c + V(x, 0, 0) + tilt * (hh * 0.95) + nrm * 0.10], [0.022, 0.022],
                      [M["brass"]], n=6), rigid("Chest"))
    hood = [(-0.62, 0.0), (0.62, 0.0), (0.50, 0.22), (-0.50, 0.22)]
    ctx.part(plate(f"{T} firebox hood", hood, 0.05, [M["iron"]], origin=c + tilt * (hh + 0.04) + nrm * 0.06, xaxis=(1, 0, 0),
                   yaxis=(0, -0.55, 0.84), bev=0.01), rigid("Chest"))
    for sd in (-1, 1):
        for o in P2.emblem(f"{T} firebox badge {sd}", c + V(sd * 1.02, 0.02, 0.0), (sd * 0.35, 0.94, 0.0), 0.19,
                           dict(gear=M["brass"], disc=M["dark"], hub=M["glow"], trim=M["trim"], spoke=M["brass"]),
                           teeth=10, depth=0.04, hub=M["glow"], spokes=4):
            ctx.part(o, rigid("Chest"))


def build_neck(ctx, M):
    """颈：粗短的蓝钢颈筒（大半被颈盾与肩甲遮住）+ 一道黄铜收口环；颈后立一面带浮雕齿轮的扇形颈盾（见 build_frill）。"""
    T = ctx.title
    pts = [V(0, 1.95, 2.66), V(0, 2.45, 2.64), V(0, 2.88, 2.62), V(0, 3.14, 2.62)]
    w = lambda p: interval_weights(p.y, [("Chest", -9, 2.3), ("Neck", 2.3, 3.0), ("Head", 3.0, 9)], 0.22)  # noqa: E731
    ctx.part(sweep(f"{T} neck", pts, [0.78, 0.74, 0.68, 0.62], [M["plate"]], n=28, per=4, tile=0.9), fn(w))
    ctx.part(trim(f"{T} neck collar", ring_points((0, 2.30, 2.62), (0, 1, -0.2), 0.80, 28), 0.05, M["trim"], closed=True),
             fn(w))


def build_frill(ctx, M):
    """颈盾（扇形盔颈）：竖在头后的叠层盾板，把龙首框在正面——外层蓝钢盾板（扇形轮廓、黄铜滚边、一圈铆钉）、
    内层黑铁凸盘 + 浮雕齿轮徽记、上缘一排黄铜后掠刺。挂 Neck 骨。"""
    T = ctx.title
    spec = rigid("Neck")
    tilt = 0.22
    ya = V(0, -math.sin(tilt), math.cos(tilt))
    base = V(0, 2.84, 2.20)
    n = (V(-1, 0, 0).cross(ya)).normalized()          # 朝前（+y）
    outline = [(-0.60, 0.0), (0.60, 0.0), (1.12, 0.45), (1.38, 1.00), (1.28, 1.55), (0.96, 1.88), (0.52, 2.00),
               (0.0, 1.88), (-0.52, 2.00), (-0.96, 1.88), (-1.28, 1.55), (-1.38, 1.00), (-1.12, 0.45)]
    ctx.part(plate(f"{T} frill plate", outline, 0.09, [M["plate"]], origin=base, xaxis=(-1, 0, 0), yaxis=ya, bev=0.014,
                   bulge=lambda x, y: 0.05 * (1 - (x / 1.4) ** 2)), spec)
    P = lambda x, y, d=0.0: base + V(-1, 0, 0) * x + ya * y + n * (0.05 + d)    # noqa: E731
    ctx.part(trim(f"{T} frill trim", [P(x * 0.97, y * 0.985 + 0.01, 0.015) for x, y in outline], 0.034, M["trim"], closed=True),
             spec)
    inner = [(-0.50, 0.14), (0.50, 0.14), (0.86, 0.52), (1.02, 0.96), (0.92, 1.36), (0.60, 1.58), (0.0, 1.50), (-0.60, 1.58),
             (-0.92, 1.36), (-1.02, 0.96), (-0.86, 0.52)]
    ctx.part(plate(f"{T} frill inner", inner, 0.07, [M["iron"]], origin=P(0, 0, 0.04) - base + base, xaxis=(-1, 0, 0), yaxis=ya,
                   bev=0.012, bulge=lambda x, y: 0.06 * (1 - (x / 1.05) ** 2)), spec)
    ctx.part(trim(f"{T} frill inner trim", [P(x * 0.96, y * 0.97 + 0.02, 0.10) for x, y in inner], 0.026, M["brass"], closed=True),
             spec)
    items = [(P(x, y, 0.12), n, 0.036) for x, y in
             ((-0.94, 0.62), (-0.86, 1.06), (-0.62, 1.42), (0.62, 1.42), (0.86, 1.06), (0.94, 0.62), (-0.34, 0.26),
              (0.34, 0.26))]
    ctx.part(studs(f"{T} frill rivets", items, [M["brass"]]), spec)
    for o in P2.emblem(f"{T} frill emblem", P(0, 0.88, 0.10), n, 0.46,
                       dict(gear=M["brass"], disc=M["dark"], hub=M["glow"], trim=M["trim"], spoke=M["brass"]), teeth=16,
                       depth=0.07, hub=M["glow"], spokes=8, hint=tuple(ya)):
        ctx.part(o, spec)
    spikes = []
    for q in range(9):
        t = (q - 4) / 4.0
        x = t * 1.05
        y = 1.62 + 0.38 * (1 - abs(t) ** 1.6) - 0.28 * abs(t) ** 1.2
        spikes.append((P(x, y, 0.0), P(x * 1.12, y + 0.30 + 0.10 * (1 - abs(t)), 0.10), 0.07))
    ctx.part(shards(f"{T} frill spikes", spikes, [M["trim"]], sides=5), spec)


# ===== 撞城龙首 =====
HB = V(0.0, 3.12, 2.67)
HF = V(0.0, 1.0, -0.07).normalized()
HL = 1.78
HS = 1.26              # 龙首整体放大（绕 HB）：头要压得住那么大的肩甲与炮塔
# 截面关键尺寸 (v: 最大半宽, 顶面半宽, 顶高, 底深, 底面半宽)：后脑宽厚、颊部外扩、向撞头收窄压低
HK = [(0.0, 0.62, 0.48, 0.50, 0.34, 0.40), (0.12, 0.88, 0.70, 0.62, 0.40, 0.56), (0.30, 0.80, 0.62, 0.52, 0.34, 0.50),
      (0.55, 0.58, 0.46, 0.42, 0.28, 0.38), (0.80, 0.42, 0.34, 0.34, 0.22, 0.28), (1.0, 0.36, 0.28, 0.30, 0.20, 0.24)]


def hs(p):
    return HB + (Vector(p) - HB) * HS


def scale_new(ctx, n0p, n0a, pivot, k):
    """把 n0p / n0a 之后新建的部件整体绕 pivot 等比缩放（网格数据按物体原点缩放，原点再按 pivot 变换）。"""
    S = Matrix.Translation(pivot) @ Matrix.Scale(k, 4) @ Matrix.Translation(-pivot)
    for o in [o for o, _ in ctx.parts[n0p:]] + [o for o, *_ in ctx.attached[n0a:]]:
        loc = o.location.copy()
        o.data.transform(Matrix.Scale(k, 4))
        o.data.update()
        o.location = S @ loc


def head_frame():
    u = V(0, 0, 1)
    u = (u - HF * u.dot(HF)).normalized()
    s = HF.cross(u).normalized()
    return HB, HF, u, s


def interp_(v, knots):
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if v <= x1:
            return lerp(y0, y1, max(0.0, min(1.0, (v - x0) / (x1 - x0))))
    return knots[-1][1]


def head_prof(v):
    return hermite(HK, v)           # [最大半宽, 顶面半宽, 顶高, 底深, 底面半宽]


def build_head(ctx, M):
    T = ctx.title
    hb, f, u, s = head_frame()
    back = hb - f * 0.25
    pos = lambda x, z, v: back + f * (v * HL) + s * x + u * z      # noqa: E731
    frame = Matrix((s, f, u)).transposed()

    def section(v, g=0.0):
        wm, wt, h, d, wb = head_prof(v)
        top = (0.0, h + g)
        right = [(wt + g * 0.6, h + g), (wm + g, h * 0.38 + g * 0.4), (wm + g, -d * 0.45), (wb + g * 0.5, -d - g)]
        return [top] + right + [(0.0, -d * 1.04 - g)] + [(-x, z) for x, z in reversed(right)]
    NV = 20
    secs = [[pos(x, z, k / (NV - 1)) for x, z in section(k / (NV - 1))] for k in range(NV)]
    skull = loft(f"{T} skull", secs, [M["plate"]], closed_u=True, cap=True, uvfn=lambda a, v: (a * 2.2, v * 2.4))
    orient(skull, lambda c: back + f * max(0.0, min(HL, (c - back).dot(f))))
    auto_smooth(skull, 28)
    ctx.part(skull, rigid("Head"))
    # 五层前倾叠甲（人字形山墙板）：后片压在前片上，前缘黄铜滚边 + 铆钉；顶面中脊隆起
    stack = [(0.76, 0.99), (0.57, 0.80), (0.38, 0.61), (0.19, 0.42), (0.02, 0.23)]
    for i, (v0, v1) in enumerate(stack):
        wr, wf = head_prof(v0)[1] + 0.05, head_prof(v1)[1] + 0.05
        p0 = pos(0, head_prof(v0)[2], v0)
        p1 = pos(0, head_prof(v1)[2], v1)
        ya = (p1 - p0).normalized()
        L = (p1 - p0).length
        lift = 0.050 + 0.030 * i
        outline = [(-wr, 0.0), (wr, 0.0), (wr * 0.97, L * 0.50), (wf, L * 0.88), (0.0, L), (-wf, L * 0.88), (-wr * 0.97, L * 0.50)]
        org = p0 + u * lift
        ctx.part(plate(f"{T} head plate {i}", outline, 0.055, [M["brass"] if i == 0 else M["iron"]], origin=org, xaxis=s, yaxis=ya,
                       bev=0.010, bulge=lambda x, y, wr=wr: 0.07 * max(0.0, 1 - abs(x) / wr)), rigid("Head"))
        edge = [org + s * x + ya * (y + 0.014) + u * (0.058 + 0.07 * max(0.0, 1 - abs(x) / wr)) for x, y in
                [outline[1]] + outline[2:5] + outline[5:7] + [outline[0]]]
        ctx.part(trim(f"{T} head plate edge {i}", edge, 0.026, M["trim"]), rigid("Head"))
        items = [(org + s * x + ya * y + u * (0.060 + 0.07 * max(0.0, 1 - abs(x) / wr)), u, 0.030)
                 for x, y in ((-wr * 0.62, L * 0.30), (wr * 0.62, L * 0.30), (-wr * 0.34, L * 0.62), (wr * 0.34, L * 0.62))]
        ctx.part(studs(f"{T} head plate rivets {i}", items, [M["trim"]]), rigid("Head"))
    # 颅顶冠刃（后掠）
    c0 = pos(0, head_prof(0.10)[2], 0.10) + u * 0.30
    crest = [(0.0, 0.0), (0.95, 0.0), (0.82, 0.17), (0.50, 0.36), (0.22, 0.43), (0.04, 0.30)]
    ctx.part(plate(f"{T} head crest", crest, 0.05, [M["plate"]], origin=c0, xaxis=f, yaxis=u, bev=0.01), rigid("Head"))
    ctx.part(trim(f"{T} head crest edge", [c0 + f * x + u * (y + 0.012) for x, y in ((0.04, 0.30), (0.22, 0.43), (0.50, 0.36),
                                                                                  (0.82, 0.17))], 0.022, M["trim"]),
             rigid("Head"))
    for sd in (-1, 1):
        # 颊侧：三道腮槽 + 颊骨刺 + 滚边
        for v in (0.18, 0.34, 0.50):
            w, _, h, d, _ = head_prof(v)
            ctx.part(trim(f"{T} cheek louver {sd}{v:.2f}", [pos(sd * (w + 0.012), -d * 0.30 + h * 0.10, v + q * 0.07)
                                                          for q in range(-1, 2)], 0.022, M["dark"]), rigid("Head"))
        w, _, h, d, _ = head_prof(0.14)
        cb = pos(sd * w, -0.02, 0.14)
        ctx.part(spike(f"{T} cheek spike {sd}", cb, cb + s * sd * 0.52 - f * 0.22 + u * 0.06, 0.12, [M["trim"]], sides=6,
                       bend=0.05), rigid("Head"))
        ctx.part(trim(f"{T} cheek edge {sd}", [pos(sd * (head_prof(v)[0] + 0.012), head_prof(v)[2] * 0.38 + 0.01, v)
                                               for v in [0.05 + 0.6 * q / 10 for q in range(11)]], 0.024, M["trim"]),
                 rigid("Head"))
    # 撞头：黄铜子弹头撞角 + 刻纹环 + 铆钉环 + 中央尖钉 + 齿轮徽记
    ram_c = back + f * (HL * 0.945) - u * 0.01
    rs, rf, ru = 0.42, 0.56, 0.37
    ctx.part(blob(f"{T} ram plate", ram_c, (rs, rf, ru), [M["brass"]], 32, 18, power=2.3, frame=frame, tile=0.5), rigid("Head"))
    for t in (-0.50, -0.05, 0.38):
        k = (1 - abs(t) ** 2.3) ** (1 / 2.3)
        ring = [ram_c + f * (t * rf) + (s * math.cos(q / 26 * TAU) * rs + u * math.sin(q / 26 * TAU) * ru) * (k + 0.012)
                for q in range(26)]
        ctx.part(trim(f"{T} ram ring {t:+.2f}", ring, 0.024, M["trim"] if t != -0.05 else M["dark"], closed=True),
                 rigid("Head"))
    for q in range(8):                                      # 放射刻纹：撞头表面八道深色刻槽
        ang = (q + 0.5) / 8 * TAU
        gp = []
        for t in [0.92 - 1.30 * i / 9 for i in range(10)]:
            kk = (1 - abs(t) ** 2.3) ** (1 / 2.3)
            gp.append(ram_c + f * (t * rf) + (s * math.sin(ang) * rs + u * math.cos(ang) * ru) * (kk + 0.010))
        ctx.part(trim(f"{T} ram groove {q}", gp, 0.016, M["dark"], n=4), rigid("Head"))
    k = (1 - 0.62 ** 2.3) ** (1 / 2.3)
    items = [(ram_c + f * (0.62 * rf) + (s * math.cos(q / 10 * TAU) * rs + u * math.sin(q / 10 * TAU) * ru) * k,
              (f * 0.5 + s * math.cos(q / 10 * TAU) * 0.6 + u * math.sin(q / 10 * TAU) * 0.6).normalized(), 0.045)
             for q in range(10)]
    ctx.part(studs(f"{T} ram studs", items, [M["trim"]]), rigid("Head"))
    tip = ram_c + f * rf
    ctx.part(spike(f"{T} ram spike", tip - f * 0.10, tip + f * 0.40, 0.12, [M["iron"]], sides=8), rigid("Head"))
    for o in P2.emblem(f"{T} ram badge", ram_c + f * (rf * 0.80) + u * 0.0, f * 0.7 + u * 0.0, 0.15,
                       dict(gear=M["iron"], disc=M["dark"], hub=M["glow"], trim=M["trim"], spoke=M["trim"]), teeth=10,
                       depth=0.04, hub=M["glow"], spokes=4, hint=tuple(u)):
        ctx.part(o, rigid("Head"))
    # 下颌（挂 Jaw 骨）：楔形颌（六角截面放样）+ 前颌甲 + 格栅齿
    hinge = back + f * 0.34 - u * 0.30
    JL = HL - 0.55

    def jprof(k):
        w = interp_(k, [(0, 0.58), (0.5, 0.50), (1, 0.32)])
        dn = interp_(k, [(0, 0.36), (0.5, 0.28), (1, 0.16)])
        return w, dn
    jsec = []
    for k in range(14):
        kk = k / 13
        w, dn = jprof(kk)
        base = hinge + f * (kk * JL) - u * 0.05
        jsec.append([base + s * x + u * z for x, z in
                     ((w * 0.9, 0.05), (w, -dn * 0.35), (w * 0.72, -dn), (0, -dn * 1.06), (-w * 0.72, -dn), (-w, -dn * 0.35),
                      (-w * 0.9, 0.05), (0, 0.05))])
    jaw = loft(f"{T} jaw", jsec, [M["plate"]], closed_u=True, cap=True, uvfn=lambda a, v: (a * 2.0, v * 1.4))
    orient(jaw, lambda c: hinge + f * max(0.0, (c - hinge).dot(f)) - u * 0.05)
    auto_smooth(jaw, 28)
    ctx.part(jaw, rigid("Jaw"))
    chin = hinge + f * JL * 0.97 - u * 0.12
    ctx.part(blob(f"{T} chin plate", chin, (0.30, 0.20, 0.19), [M["brass"]], 20, 10, power=2.8, frame=frame, tile=0.5),
             rigid("Jaw"))
    for sd in (-1, 1):
        ctx.part(trim(f"{T} jaw edge {sd}", [hinge + f * (kk * JL) - u * 0.05 + s * sd * (jprof(kk)[0] + 0.012) + u * 0.02
                                             for kk in [0.04 + 0.92 * q / 12 for q in range(13)]], 0.024, M["trim"]),
                 rigid("Jaw"))
    ctx.part(blob(f"{T} maw glow", hinge + f * 0.60, (0.30, 0.45, 0.05), [M["core"]], 16, 8, frame=frame), rigid("Jaw"))
    up_t, dn_t = [], []
    for k in range(10):
        v = 0.34 + k * 0.060
        wm, wt, h, d, wb = head_prof(v)
        for sd in (-1, 1):
            base = back + f * (v * HL) + s * sd * wb * 0.78 - u * d * 0.95
            up_t.append((base + u * 0.05, base - u * 0.20 + f * 0.03, 0.045))
            jb = hinge + f * (v * HL - 0.38) + s * sd * wb * 0.70 - u * 0.04
            dn_t.append((jb - u * 0.04, jb + u * 0.17, 0.040))
    ctx.part(shards(f"{T} grille teeth", up_t, [M["steel"]], sides=4), rigid("Head"))
    ctx.part(shards(f"{T} lower grille teeth", dn_t, [M["steel"]], sides=4), rigid("Jaw"))
    # 前格栅：撞头下方一排竖栅条（散热格栅，随头走）
    for q in range(7):
        x = (q - 3) * 0.095
        b0 = back + f * (HL * 0.86) - u * 0.27 + s * x
        ctx.part(tube(f"{T} grille bar {q}", [b0, b0 - u * 0.17], [0.028, 0.022], [M["steel"]], n=5, per=1), rigid("Head"))
    # 琥珀眼缝（深陷）：前向眼匣（黑铁匣体 + 黄铜框）里只露一道斜向的琥珀缝，重眉铁压在上方、颊板托在下方
    for sd in (-1, 1):
        v = 0.56
        wm, wt, h, d, wb = head_prof(v)
        xm, zm = (wt + wm) / 2, (h + h * 0.38) / 2
        nx, nz = 0.62 * h, wm - wt                           # 上侧斜面的外法向（x, z）
        nl = math.hypot(nx, nz)
        E = pos(sd * xm, zm, v) + (s * sd * nx + u * nz) * (0.12 / nl)
        ctx.part(blob(f"{T} eye housing {sd}", E, (0.31, 0.27, 0.20), [M["iron"]], 22, 12, power=2.8, frame=frame, tile=0.5),
                 rigid("Head"))
        fc = E + f * 0.262
        xa = s * sd
        slit = [(-0.26, -0.030), (0.26, 0.090), (0.26, 0.170), (-0.26, 0.050)]
        ctx.part(plate(f"{T} eye {sd}", slit, 0.035, [M["core"]], origin=fc, xaxis=xa, yaxis=u), rigid("Head"))
        rim = [fc + xa * (x * 1.30) + u * ((y - 0.05) * 1.9 + 0.06) + f * 0.012 for x, y in slit]
        ctx.part(trim(f"{T} eye rim {sd}", rim, 0.026, M["trim"], closed=True, n=5), rigid("Head"))
        brow = [E + f * 0.08 + xa * (x * 1.45) + u * (0.25 + 0.075 * x / 0.2 * 0.5) for x in (-0.28, -0.14, 0.0, 0.14, 0.28)]
        ctx.part(tube(f"{T} brow iron {sd}", brow, [0.050, 0.085, 0.098, 0.088, 0.060], [M["iron"]], n=6, fy=0.7,
                      up=tuple(u)), rigid("Head"))
        ctx.part(trim(f"{T} brow trim {sd}", [p + u * 0.07 + f * 0.02 for p in brow[1:-1]], 0.02, M["trim"]), rigid("Head"))
    # 颊侧叠板：竖壁上两片错叠的黑铁板（黄铜滚边 + 铆钉）+ 颚铰链齿轮徽记
    for sd in (-1, 1):
        for i, (va, vb) in enumerate(((0.44, 0.72), (0.62, 0.92))):
            pa_ = pos(sd * (head_prof(va)[0] + 0.015 + 0.02 * i), -0.02, va)
            pb_ = pos(sd * (head_prof(vb)[0] + 0.015 + 0.02 * i), -0.02, vb)
            xa = (pb_ - pa_).normalized() * sd
            Lc = (pb_ - pa_).length
            hh = head_prof((va + vb) / 2)[2] * 0.30 + head_prof((va + vb) / 2)[3] * 0.45
            ol = [(0.0, -hh), (Lc * 0.92, -hh * 0.82), (Lc, 0.0), (Lc * 0.92, hh * 0.9), (0.0, hh)]
            ctx.part(plate(f"{T} cheek plate {sd}{i}", ol, 0.05,
                           [M["iron"] if i == 0 else M["plate"]], origin=pa_, xaxis=xa, yaxis=u, bev=0.008), rigid("Head"))
            ctx.part(trim(f"{T} cheek plate trim {sd}{i}", [pa_ + xa * x + u * y + (s * sd) * 0.03 for x, y in ol] + [pa_ + xa * ol[0][0] + u * ol[0][1] + (s * sd) * 0.03],
                          0.020, M["trim"]), rigid("Head"))
            items = [(pa_ + xa * (Lc * t) + u * y + (s * sd) * 0.032, s * sd, 0.028) for t, y in ((0.2, hh * 0.6), (0.2, -hh * 0.6), (0.7, 0.0))]
            ctx.part(studs(f"{T} cheek plate rivets {sd}{i}", items, [M["brass"]]), rigid("Head"))
        for o in P2.emblem(f"{T} jaw hinge {sd}", pos(sd * (head_prof(0.10)[0] + 0.03), -0.10, 0.10), s * sd, 0.30,
                           dict(gear=M["brass"], disc=M["dark"], hub=M["glow"], trim=M["trim"], spoke=M["brass"]), teeth=12,
                           depth=0.05, hub=M["glow"], spokes=6, hint=tuple(u)):
            ctx.part(o, rigid("Head"))
    # 铜鼻环
    nc = back + f * (HL * 0.80) - u * 0.34
    ring = [nc + (f * math.cos(q) * 0.5 + u * math.sin(q)) * 0.17 for q in [i / 20 * TAU for i in range(20)]]
    ctx.part(trim(f"{T} nose ring", ring, 0.032, M["trim"], closed=True), rigid("Head"))
    build_horns(ctx, M, back, f, u, s)


def build_horns(ctx, M, back, f, u, s):
    """分节锤角：从颅顶后角起，向外 → 上 → 前弯成粗壮的新月（三次贝塞尔），角身七节（节间收腰），节缝套黄铜环、
    角尖黄铜帽；角根是黄铜锥形座（带铆钉箍）。角抬在脑后上方，眼缝与颊甲留在脸上。"""
    T = ctx.title
    N = 7
    for sd in (-1, 1):
        B = back + f * 0.34 + u * 0.46 + s * sd * 0.56
        P = [B, B + s * sd * 0.68 + u * 0.10 - f * 0.28, B + s * sd * 1.16 + u * 0.44 + f * 0.08, B + s * sd * 1.02 + u * 0.78 + f * 0.80]
        n = 38
        pts = []
        for i in range(n + 1):
            t = i / n
            q = (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t * t * P[2] + t ** 3 * P[3]
            pts.append(q)
        radii = [0.35 * (1 - 0.56 * (i / n) ** 0.9) + 0.02 for i in range(n + 1)]

        def seg(a, t):
            ph = (t * N) % 1.0
            return 0.88 + 0.16 * math.sin(math.pi * ph) ** 0.6
        ctx.part(sweep(f"{T} horn {sd}", pts, radii, [M["horn"]], n=16, per=2, shape=seg, tile=0.6), rigid("Head"))
        d0 = (pts[1] - pts[0]).normalized()
        a0 = d0.orthogonal().normalized()
        b0 = d0.cross(a0)
        cone = sweep(f"{T} horn socket {sd}", [pts[0] - d0 * 0.22, pts[0] + d0 * 0.02, pts[0] + d0 * 0.20], [0.42, 0.38, 0.34],
                     [M["brass"]], n=20, per=2, tile=0.5)
        ctx.part(cone, rigid("Head"))
        for dz, r in ((-0.12, 0.405), (0.12, 0.36)):
            ctx.part(trim(f"{T} horn socket ring {sd}{dz}", ring_points(pts[0] + d0 * dz, d0, r, 22), 0.03, M["trim"],
                          closed=True, n=5), rigid("Head"))
        items = [(pts[0] - d0 * 0.02 + (a0 * math.cos(q) + b0 * math.sin(q)) * 0.395,
                  a0 * math.cos(q) + b0 * math.sin(q), 0.034) for q in [i / 10 * TAU for i in range(10)]]
        ctx.part(studs(f"{T} horn socket rivets {sd}", items, [M["trim"]]), rigid("Head"))
        for j in range(1, N):                               # 节缝黄铜环
            i = min(n - 1, max(1, int(round(j / N * n))))
            dd = (pts[i + 1] - pts[i - 1]).normalized()
            ctx.part(trim(f"{T} horn band {sd}.{j}", ring_points(pts[i], dd, radii[i] * 1.00, 20), 0.032, M["trim"],
                          closed=True, n=5), rigid("Head"))
        tip0, tip1 = pts[-2], pts[-1]
        d = (tip1 - tip0).normalized()
        # 锤头：黄铜重锤帽（长椭球）+ 两道箍 + 铁尖
        hc = tip1 + d * 0.10
        ctx.part(blob(f"{T} horn hammer {sd}", hc, (0.25, 0.25, 0.34), [M["brass"]], 22, 12, power=2.4,
                      frame=Matrix((d.orthogonal().normalized(), d.cross(d.orthogonal().normalized()), d)).transposed(), tile=0.5),
                 rigid("Head"))
        for dz in (-0.10, 0.10):
            ctx.part(trim(f"{T} horn hammer ring {sd}{dz}", ring_points(hc + d * dz, d, 0.255, 20), 0.03, M["dark"], closed=True,
                          n=5), rigid("Head"))
        ctx.part(spike(f"{T} horn cap {sd}", hc + d * 0.28, hc + d * 0.58, 0.10, [M["iron"]], sides=8), rigid("Head"))


# ===== 炮塔与攻城炮 =====
TURRET_C = V(0.0, -0.45, 0.0)
TRUNNION = V(0.0, 0.30, 4.20)
MUZZLE = V(0.0, 3.70, 4.20)
T_PIVOT = V(0.0, -0.45, 3.45)


def build_turret(ctx, M):
    """炮塔节点（BOSS_2_TURRET）包含全部炮塔件：座圈、棱面塔身、前弧护盾板、环形尖刺、仪表、顶部瞄准镜与指挥塔、
    天线组、旗杆与燕尾旗——网页端旋转该节点时它们一起转。炮管（BOSS_2_CANNON）与炮口焰（BOSS_2_MUZZLE）另成节点。"""
    T = ctx.title
    objs = []
    cx, cy = TURRET_C.x, TURRET_C.y
    objs.append(lathe(f"{T} turret ring", [(1.30, 3.45), (1.36, 3.52), (1.42, 3.62), (1.36, 3.72), (1.24, 3.76)],
                      [M["trim"]], 56, center=TURRET_C))
    objs.append(lathe(f"{T} turret gear ring", [(1.40, 3.40), (1.46, 3.46), (1.46, 3.54), (1.40, 3.58)], [M["dark"]], 56,
                      center=TURRET_C))
    body = lathe(f"{T} turret body", [(1.22, 3.76), (1.20, 4.02), (1.10, 4.30), (0.90, 4.52), (0.55, 4.66), (0.0, 4.70)],
                 [M["plate"]], 14, center=TURRET_C, sy=1.12)
    auto_smooth(body, 20)
    objs.append(body)
    objs.append(lathe(f"{T} turret roof ring", [(0.60, 4.64), (0.64, 4.69), (0.58, 4.74)], [M["trim"]], 40, center=TURRET_C))
    objs.append(blob(f"{T} turret lens", TURRET_C + V(0, 0, 4.72), (0.30, 0.30, 0.05), [M["glow"]], 24, 8))
    objs.append(lathe(f"{T} turret lens ring", [(0.36, 4.69), (0.38, 4.75), (0.33, 4.78)], [M["trim"]], 40, center=TURRET_C))
    cup = TURRET_C + V(0.0, -0.58, 0.0)
    objs.append(lathe(f"{T} cupola", [(0.32, 4.40), (0.34, 4.74), (0.30, 4.82), (0.0, 4.84)], [M["plate"]], 20, center=cup))
    objs.append(tube(f"{T} cupola slits", ring_points(cup + V(0, 0, 4.64), (0, 0, 1), 0.342, 24), [0.024] * 24,
                     [M["glow"]], n=6, closed=True))
    items = [(TURRET_C + V(math.sin(a) * 1.44, math.cos(a) * 1.44, 3.60), V(math.sin(a), math.cos(a), 0.2), 0.04)
             for a in [q / 30 * TAU for q in range(30)]]
    objs.append(studs(f"{T} turret rivets", items, [M["brass"]]))
    # 前弧护盾板：六块外倾的棱面装甲板（中间留炮口位），每块黄铜边框 + 琥珀瞄孔 + 角铆钉
    for ang_d in (-82, -54, -26, 26, 54, 82):
        ang = math.radians(ang_d)
        rh = V(math.sin(ang), math.cos(ang), 0)
        tg = V(math.cos(ang), -math.sin(ang), 0)
        tilt = 0.30
        ya = V(0, 0, math.cos(tilt)) - rh * math.sin(tilt)
        base = TURRET_C + rh * 1.30 + V(0, 0, 3.80)
        outline = [(-0.30, 0.0), (0.30, 0.0), (0.33, 0.62), (0.22, 0.98), (-0.22, 0.98), (-0.33, 0.62)]
        objs.append(plate(f"{T} turret shield {ang_d}", outline, 0.07, [M["plate"]], origin=base, xaxis=-tg, yaxis=ya,
                          bev=0.012))
        nrm = rh * math.cos(tilt) + V(0, 0, math.sin(tilt))
        edge = [base + (-tg) * (x * 0.90) + ya * (y * 0.93 + 0.03) + nrm * 0.044 for x, y in outline]
        objs.append(trim(f"{T} turret shield trim {ang_d}", edge, 0.022, M["trim"], closed=True, n=5))
        slit = [(-0.14, 0.42), (0.14, 0.42), (0.14, 0.47), (-0.14, 0.47)]
        objs.append(plate(f"{T} turret shield slit {ang_d}", slit, 0.02, [M["core"]], origin=base + nrm * 0.040, xaxis=-tg,
                          yaxis=ya))
        riv = [(base + (-tg) * x + ya * y + nrm * 0.048, nrm, 0.030) for x, y in ((-0.22, 0.10), (0.22, 0.10), (-0.24, 0.80),
                                                                              (0.24, 0.80))]
        objs.append(studs(f"{T} turret shield rivets {ang_d}", riv, [M["brass"]]))
    # 环形装饰尖刺：座圈外缘一圈后掠短刺（黄铜）
    sp = []
    for q in range(16):
        a = q / 16 * TAU
        rh = V(math.sin(a), math.cos(a), 0)
        b = TURRET_C + rh * 1.46 + V(0, 0, 3.58)
        sp.append((b, b + rh * 0.34 + V(0, 0, 0.20), 0.07))
    objs.append(shards(f"{T} turret crown spikes", sp, [M["trim"]], sides=5))
    # 炮塔侧仪表
    for sd in (-1, 1):
        objs += gauge(ctx, M, TURRET_C + V(sd * 1.22, 0.30, 4.04), V(sd, 0.15, 0.1).normalized(), None, f"turret{sd}", 0.16,
                      needle=0.4 * sd)
        for o in P2.emblem(f"{T} turret badge {sd}", TURRET_C + V(sd * 1.15, -0.55, 4.10), V(sd, 0, 0.18), 0.25,
                           dict(gear=M["brass"], disc=M["dark"], hub=M["glow"], trim=M["trim"], spoke=M["brass"]),
                           teeth=12, depth=0.05, hub=M["glow"], spokes=6, hint=(0, 1, 0)):
            objs.append(o)
    # 天线组：三根不同高度的鞭状天线 + 琥珀灯；一根旗杆挂燕尾旗
    for k, (x, y, h) in enumerate(((0.62, -0.62, 1.10), (-0.55, -0.80, 0.80), (0.20, -1.10, 0.62))):
        a0 = TURRET_C + V(x, y + 0.3, 4.40)
        a1 = a0 + V(0.04 * x, -0.15, h)
        objs.append(tube(f"{T} antenna {k}", [a0, a1], [0.030, 0.010], [M["dark"]], n=6))
        objs.append(gem(f"{T} antenna light {k}", a1, 0.045, M["glow"], (1, 1, 1)))
        objs.append(trim(f"{T} antenna collar {k}", ring_points(a0 + V(0, 0, 0.10), (0, 0, 1), 0.05, 10), 0.016,
                         M["trim"], closed=True, n=4))
    pole0 = TURRET_C + V(-0.05, -1.00, 4.52)
    pole1 = pole0 + V(0, 0, 1.55)
    objs.append(tube(f"{T} banner pole", [pole0, pole1], [0.045, 0.03], [M["trim"]], n=8))
    objs.append(blob(f"{T} banner finial", pole1 + V(0, 0, 0.05), (0.07, 0.07, 0.07), [M["brass"]], 12, 8))
    objs.append(spike(f"{T} banner spike", pole1 + V(0, 0, 0.08), pole1 + V(0, 0, 0.34), 0.04, [M["trim"]], sides=6))
    flag = [(0.0, 0.0), (-1.00, 0.04), (-0.78, -0.28), (-1.00, -0.58), (0.0, -0.58)]
    fo = pole1 + V(0.0, -0.02, -0.12)
    objs.append(plate(f"{T} banner", flag, 0.03, [M["plate"]], origin=fo, xaxis=(0, -1, 0), yaxis=(0, 0, 1), bev=0.006))
    edge = [fo + V(0.026, 0, 0) + V(0, -1, 0) * x * 0.97 + V(0, 0, 1) * (y * 0.94 - 0.02) for x, y in flag[1:]]
    objs.append(trim(f"{T} banner trim", edge, 0.018, M["trim"], n=5))
    for sd in (-1, 1):
        for o in P2.emblem(f"{T} banner badge {sd}", fo + V(sd * 0.017, 0, 0) + V(0, -0.40, -0.27), V(sd, 0, 0), 0.15,
                           dict(gear=M["brass"], disc=M["dark"], hub=M["glow"], trim=M["trim"], spoke=M["brass"]),
                           teeth=10, depth=0.02, hub=M["glow"], spokes=4, hint=(0, 0, 1)):
            objs.append(o)
    node = join(objs, f"{ctx.ID}_TURRET", T_PIVOT)
    ctx.attach(node, "Turret", keep=True)
    # 炮盾（挂 Cannon 骨：随炮管俯仰）与炮耳
    ctx.part(blob(f"{T} mantlet", TRUNNION + V(0, 0.12, 0), (0.56, 0.34, 0.42), [M["plate"]], 28, 14, power=3.0), rigid("Cannon"))
    ctx.part(trim(f"{T} mantlet ring", ring_points(TRUNNION + V(0, 0.38, 0), (0, 1, 0), 0.40, 28), 0.04, M["trim"],
                  closed=True), rigid("Cannon"))
    for o in P2.emblem(f"{T} mantlet badge", TRUNNION + V(0, 0.40, 0.0), (0, 1, 0), 0.26,
                       dict(gear=M["trim"], disc=M["dark"], hub=M["glow"], trim=M["trim"], spoke=M["brass"]), teeth=12,
                       depth=0.05, hub=M["glow"], spokes=6, hint=(0, 0, 1)):
        ctx.part(o, rigid("Cannon"))
    for sd in (-1, 1):
        ob = lathe(f"{T} trunnion {sd}", [(0.16, 0.0), (0.18, 0.06), (0.11, 0.11)], [M["trim"]], 20, center=(0, 0, 0))
        ob.data.transform(Matrix.Translation(TRUNNION + V(sd * 0.54, 0.12, 0)) @ Matrix.Rotation(sd * math.pi / 2, 4, "Y"))
        ctx.part(ob, rigid("Cannon"))
    y = [0.40, 1.10, 1.90, 2.70, 3.14]
    barrel = [sweep(f"{T} barrel", [TRUNNION + V(0, yy, 0) for yy in y], [0.30, 0.28, 0.26, 0.245, 0.245], [M["iron"]], n=24,
                    per=3, up=(0, 0, 1), tile=0.8)]
    for k, yy in enumerate((0.62, 1.40, 2.12, 2.80)):
        barrel.append(trim(f"{T} barrel hoop {k}", ring_points(TRUNNION + V(0, yy, 0), (0, 1, 0), 0.30 - 0.014 * k, 28), 0.04,
                           M["trim"], closed=True))
    barrel.append(blob(f"{T} fume extractor", TRUNNION + V(0, 1.72, 0), (0.34, 0.30, 0.34), [M["plate"]], 24, 12, power=2.6))
    barrel.append(trim(f"{T} extractor ring", ring_points(TRUNNION + V(0, 1.72, 0), (0, 1, 0), 0.352, 28), 0.032, M["trim"],
                       closed=True))
    brake = TRUNNION + V(0, 3.30, 0)
    barrel.append(blob(f"{T} muzzle brake", brake, (0.34, 0.26, 0.30), [M["plate"]], 24, 12, power=3.4))
    for sd in (-1, 1):
        for k in range(3):
            barrel.append(blob(f"{T} brake vent {sd}{k}", brake + V(sd * 0.335, (k - 1) * 0.14, 0), (0.02, 0.045, 0.13),
                               [M["core"]], 8, 6))
    barrel.append(blob(f"{T} bore glow", MUZZLE - V(0, 0.02, 0), (0.13, 0.02, 0.13), [M["core"]], 16, 6))
    ctx.attach(join(barrel, f"{ctx.ID}_CANNON", TRUNNION), "Barrel", keep=True)
    muzzle = [P2.flame_sheets(f"{T} muzzle flash", MUZZLE, (0, 1, 0), 1.25, 0.30, [M["flame"]], n=5, seed=0.4),
              P2.flame_sheets(f"{T} muzzle flash core", MUZZLE, (0, 1, 0), 0.75, 0.16, [M["flamehot"]], n=3, seed=1.1)]
    node = join(muzzle, f"{ctx.ID}_MUZZLE", MUZZLE)
    if "--geo" in sys.argv:                      # 纯几何审图没有姿态，炮口焰会以满尺寸挡住炮管
        node.hide_render = True
    ctx.attach(node, "Muzzle", keep=True)


# ===== 烟囱与排气口 =====
STACKS = [V(sd * 0.55, -2.30, 4.88) for sd, _ in SIDES]
VENTS = [V(sd * 0.88, 1.62, 4.42) for sd, _ in SIDES]


def nozzle(ctx, M, tag, mouth, d, r, bone, h_out, w_out, seed):
    """喷口：烧红的喷口环 + 炽热光盘 + 薄片状半透明火舌（外焰 + 内焰两层），火舌挂 bone 随倍率伸缩。"""
    T = ctx.title
    ctx.part(trim(f"{T} {tag} hot ring", ring_points(mouth + d * 0.01, d, r, 22), 0.034, M["core"], closed=True, n=6),
             rigid(bone))
    ctx.attach(P2.flame_sheets(f"{T} {tag} flame", mouth + d * 0.02, d, h_out, w_out, [M["flame"]], n=3, seed=seed), f"{tag}")
    ctx.attach(P2.flame_sheets(f"{T} {tag} flame core", mouth + d * 0.02, d, h_out * 0.60, w_out * 0.50, [M["flamehot"]], n=2,
                               seed=seed + 0.5), f"{tag}")


def build_stacks(ctx, M):
    T = ctx.title
    for (sd, label), top in zip(SIDES, STACKS):
        x, y = top.x, top.y
        ctx.part(sweep(f"{T} stack {label}", [(x, y + 0.02, 3.0), (x, y, 3.8), (x, y - 0.02, 4.55)], [0.31, 0.27, 0.23],
                       [M["iron"]], n=18, per=3, tile=0.7), rigid("Rump"))
        for z, r in ((3.45, 0.30), (3.95, 0.265), (4.38, 0.24)):
            ctx.part(trim(f"{T} stack band {label}{z}", ring_points((x, y, z), (0, 0, 1), r + 0.012, 20), 0.032, M["trim"],
                          closed=True), rigid("Rump"))
        ctx.part(lathe(f"{T} stack crown {label}", [(0.22, 4.60), (0.34, 4.72), (0.40, 4.80), (0.36, 4.86), (0.27, 4.82)],
                       [M["brass"]], 28, center=(x, y, 0)), rigid("Rump"))
        for q in range(8):
            a = q / 8 * TAU
            b = V(x + math.sin(a) * 0.38, y + math.cos(a) * 0.38, 4.82)
            ctx.part(spike(f"{T} stack spike {label}{q}", b, b + V(math.sin(a) * 0.12, math.cos(a) * 0.12, 0.28), 0.045,
                           [M["trim"]], sides=4), rigid("Rump"))
        ctx.part(blob(f"{T} stack fire {label}", (x, y, 4.84), (0.24, 0.24, 0.03), [M["core"]], 16, 6), rigid("Rump"))
        nozzle(ctx, M, f"Stack.{label}", top, V(0, 0, 1), 0.27, "Rump", 0.95, 0.30, sd)
    for (sd, label), mouth in zip(SIDES, VENTS):
        root = V(sd * 0.64, 1.96, 3.56)
        mid = V(sd * 0.78, 1.80, 3.98)
        ctx.part(sweep(f"{T} vent pipe {label}", [root, mid, mouth], [0.19, 0.17, 0.155], [M["trim"]], n=14, per=3),
                 rigid("Chest"))
        d = (mouth - mid).normalized()
        ctx.part(trim(f"{T} vent lip {label}", ring_points(mouth, d, 0.185, 18), 0.038, M["brass"], closed=True),
                 rigid("Chest"))
        ctx.part(blob(f"{T} vent fire {label}", mouth - d * 0.02, (0.14, 0.14, 0.14), [M["core"]], 12, 6), rigid("Chest"))
        nozzle(ctx, M, f"Vent.{label}", mouth, d, 0.15, "Chest", 0.70, 0.22, 2 + sd)


# ===== 四腿（反关节重型机械腿）=====
PAD_R = 0.66


def leg_joints():
    """腿按最终（已含 ZB）坐标定义：前腿肘向后、后腿膝向前（反关节）。"""
    legs = {}
    for sd, s in SIDES:
        legs[("Fore", s)] = dict(sd=sd, top=V(sd * 1.45, 1.45, 2.50 + ZB), mid=V(sd * 1.86, 0.95, 1.42 + 0.18),
                                 ankle=V(sd * 1.62, 1.62, 0.54), toe=V(sd * 1.62, 2.30, 0.30), parent="Chest")
        legs[("Hind", s)] = dict(sd=sd, top=V(sd * 1.42, -1.85, 2.55 + ZB), mid=V(sd * 1.90, -1.15, 1.50 + 0.18),
                                 ankle=V(sd * 1.62, -2.00, 0.56), toe=V(sd * 1.62, -1.35, 0.30), parent="Rump")
    for L in legs.values():
        d = (L["ankle"] - L["top"]).normalized()
        pv = L["mid"] - L["top"]
        L["pole"] = (pv - d * pv.dot(d)).normalized()
        o = V(L["sd"], 0, 0)
        # 外侧液压缸（A / B）：跨过膝外侧；内角液压缸（C / D）：压在“膝弯”内侧
        L["pa"] = L["top"].lerp(L["mid"], 0.30) + o * 0.58
        L["pb"] = L["mid"].lerp(L["ankle"], 0.46) + o * 0.50
        L["pc"] = L["top"].lerp(L["mid"], 0.50) - L["pole"] * 0.60
        L["pd"] = L["mid"].lerp(L["ankle"], 0.42) - L["pole"] * 0.52
        L["foot_dir"] = (L["toe"] - L["ankle"]).normalized()
    return legs


def leg_frame(p0, p1, sd):
    d = (p1 - p0).normalized()
    o = V(sd, 0, 0)
    o = (o - d * o.dot(d)).normalized()
    return d, o, d.cross(o)


def build_legs(ctx, M, legs):
    T = ctx.title
    for (leg, s), L in legs.items():
        sd = L["sd"]
        up, lo, ft = f"{leg}Up.{s}", f"{leg}Low.{s}", f"{leg}Foot.{s}"
        top, mid, ank = L["top"], L["mid"], L["ankle"]
        d1, o1, w1 = leg_frame(top, mid, sd)
        d2, o2, w2 = leg_frame(mid, ank, sd)
        pole = L["pole"]
        # --- 大腿：粗壮铁柱，三道分节环（黄铜 / 深色 / 黄铜）---
        rad = lambda t: lerp(0.60, 0.44, t)   # noqa: E731
        ctx.part(sweep(f"{T} {leg} thigh {s}", [top - d1 * 0.35, top.lerp(mid, 0.33), top.lerp(mid, 0.66), mid],
                       [0.56, 0.62, 0.54, 0.44], [M["iron"]], n=20, per=3, tile=0.8), rigid(up))
        for t, mat in ((0.16, "trim"), (0.46, "dark"), (0.78, "trim")):
            ctx.part(trim(f"{T} {leg} thigh ring {s}{t}", ring_points(top.lerp(mid, t), d1, rad(t) + 0.02, 24), 0.042, M[mat],
                          closed=True), rigid(up))
        # 外侧护肩半壳（蓝钢）+ 黄铜下缘 + 铆钉 + 琥珀灯
        def sh(u, v, top=top, mid=mid, o=o1, w=w1):
            t = lerp(-0.10, 0.66, v)
            c = top + (mid - top) * t
            b = lerp(-1.55, 1.55, u)
            r = 0.72 - 0.14 * max(0.0, t)
            return c + (o * math.cos(b) + w * math.sin(b)) * r
        guard = surface(f"{T} {leg} guard {s}", sh, 22, 10, [M["plate"]], uvfn=lambda u, v: (u * 1.6, v * 1.2))
        orient(guard, lambda c, top=top, d=d1: top + d * (c - top).dot(d))
        ctx.part(finish(guard, 0.05, -1, 0), rigid(up))
        rim = [sh(i / 20, 1.0) + ((sh(i / 20, 1.0) - (top + (mid - top) * 0.66)).normalized()) * 0.03 for i in range(21)]
        ctx.part(trim(f"{T} {leg} guard rim {s}", rim, 0.038, M["trim"]), rigid(up))
        items = [(sh(u_, 0.30) + (sh(u_, 0.30) - (top + (mid - top) * 0.02)).normalized() * 0.03,
                  (sh(u_, 0.30) - (top + (mid - top) * 0.02)).normalized(), 0.04) for u_ in [0.12, 0.3, 0.5, 0.7, 0.88]]
        ctx.part(studs(f"{T} {leg} guard rivets {s}", items, [M["brass"]]), rigid(up))
        ctx.part(gem(f"{T} {leg} guard lamp {s}", sh(0.5, 0.58) + o1 * 0.05, 0.065, M["glow"], (1, 1, 1)), rigid(up))
        # --- 膝 / 肘：黄铜球帽 + 双侧轮毂盘 + 外侧齿轮徽记 + 膝刺 ---
        ctx.part(blob(f"{T} {leg} knee {s}", mid, (0.46, 0.46, 0.46), [M["brass"]], 22, 12, tile=0.5), rigid(lo))
        for sg in (1, -1):
            ctx.part(trim(f"{T} {leg} knee ring {s}{sg}", ring_points(mid + o1 * (0.40 * sg), o1, 0.30, 20), 0.045,
                          M["dark"], closed=True), rigid(lo))
        for o in P2.emblem(f"{T} {leg} knee badge {s}", mid + o1 * 0.43, o1, 0.27,
                           dict(gear=M["iron"], disc=M["dark"], hub=M["glow"], trim=M["trim"], spoke=M["trim"]), teeth=10,
                           depth=0.05, hub=M["glow"], spokes=5, hint=(0, 0, 1)):
            ctx.part(o, rigid(lo))
        ctx.part(spike(f"{T} {leg} knee spike {s}", mid + o1 * 0.35 + pole * 0.12, mid + o1 * 0.70 + pole * 0.55, 0.11,
                       [M["trim"]], sides=7), rigid(lo))
        # --- 小腿：柱状（底端加粗）+ 外侧厚重护胫（半壳 + 中脊 + 滚边 + 铆钉）---
        ctx.part(sweep(f"{T} {leg} shin {s}", [mid, mid.lerp(ank, 0.35), mid.lerp(ank, 0.70), ank + V(0, 0, 0.08)],
                       [0.44, 0.40, 0.44, 0.50], [M["iron"]], n=20, per=3, tile=0.8), rigid(lo))

        def gr(u, v, mid=mid, ank=ank, o=o2, w=w2):
            t = lerp(0.12, 0.90, v)
            c = mid.lerp(ank, t)
            b = lerp(-1.75, 1.75, u)
            r = 0.58 - 0.02 * t
            return c + (o * math.cos(b) + w * math.sin(b)) * r
        greave = surface(f"{T} {leg} greave {s}", gr, 18, 10, [M["plate"]], uvfn=lambda u, v: (u * 1.4, v * 1.4))
        orient(greave, lambda c, mid=mid, d=d2: mid + d * (c - mid).dot(d))
        ctx.part(finish(greave, 0.05, -1, 0), rigid(lo))
        for v in (0.0, 1.0):
            pts = [gr(i / 16, v) + (gr(i / 16, v) - mid.lerp(ank, lerp(0.12, 0.90, v))).normalized() * 0.03 for i in range(17)]
            ctx.part(trim(f"{T} {leg} greave rim {s}{v:.0f}", pts, 0.036, M["trim"]), rigid(lo))
        ctx.part(trim(f"{T} {leg} greave rib {s}", [gr(0.5, i / 8) + o2 * 0.035 for i in range(9)], 0.034, M["brass"]),
                 rigid(lo))
        items = [(gr(u_, 0.14) + (gr(u_, 0.14) - mid.lerp(ank, 0.20)).normalized() * 0.03,
                  (gr(u_, 0.14) - mid.lerp(ank, 0.20)).normalized(), 0.036) for u_ in (0.2, 0.35, 0.65, 0.8)]
        ctx.part(studs(f"{T} {leg} greave rivets {s}", items, [M["brass"]]), rigid(lo))
        # 踝：黄铜球帽 + 收口环
        ctx.part(blob(f"{T} {leg} ankle {s}", ank + V(0, 0, 0.06), (0.38, 0.38, 0.36), [M["brass"]], 18, 10, tile=0.5),
                 rigid(ft))
        ctx.part(trim(f"{T} {leg} ankle ring {s}", ring_points(ank + V(0, 0, 0.30), d2, 0.40, 22), 0.045, M["dark"],
                      closed=True), rigid(lo))
        # --- 液压活塞：缸筒挂上腿、活塞杆挂下腿（每帧两端互相对准）；A/B 外侧、C/D 内角 ---
        for (a_k, b_k, pn, qn, ca, cb) in (("pa", "pb", "A", "B", 0.125, 0.068), ("pc", "pd", "C", "D", 0.105, 0.058)):
            pa, pb = L[a_k], L[b_k]
            dd = (pb - pa)
            ctx.attach(sweep(f"{T} {leg} cylinder {pn} {s}", [pa, pa + dd * 0.60], [ca, ca], [M["brass"]], n=12, per=1),
                       f"{leg}Piston{pn}.{s}")
            ctx.attach(sweep(f"{T} {leg} rod {qn} {s}", [pb, pb - dd * 0.66], [cb, cb], [M["steel"]], n=10, per=1),
                       f"{leg}Piston{qn}.{s}")
            ctx.attach(trim(f"{T} {leg} cylinder cap {pn} {s}", ring_points(pa + dd * 0.60, dd, ca * 1.15, 12), 0.022,
                            M["trim"], closed=True), f"{leg}Piston{pn}.{s}")
            ctx.part(blob(f"{T} {leg} piston mount {pn} {s}", pa, (0.11, 0.11, 0.11), [M["dark"]], 12, 8), rigid(up))
            ctx.part(blob(f"{T} {leg} piston mount {qn} {s}", pb, (0.09, 0.09, 0.09), [M["dark"]], 12, 8), rigid(lo))
        # --- 蹄：铁蹄跟 + 黄铜箍 + 三根楔形趾（趾箍 + 粗弯爪）+ 脚跟刺 ---
        pc = V(ank.x, ank.y + 0.06, 0.0)
        ctx.part(lathe(f"{T} {leg} pad {s}", [(0.36, 0.64), (0.46, 0.56), (0.58, 0.42), (0.66, 0.24), (0.64, 0.07),
                                              (0.56, 0.0), (0.0, 0.0)], [M["iron"]], 28, center=pc), rigid(ft))
        ctx.part(trim(f"{T} {leg} pad band {s}", ring_points(pc + V(0, 0, 0.44), (0, 0, 1), 0.58, 24), 0.04, M["trim"],
                      closed=True), rigid(ft))
        ctx.part(trim(f"{T} {leg} pad band low {s}", ring_points(pc + V(0, 0, 0.14), (0, 0, 1), 0.66, 24), 0.032, M["dark"],
                      closed=True), rigid(ft))
        for k in (-1, 0, 1):
            a = k * 0.72
            dv = V(math.sin(a), math.cos(a), 0)
            sv = V(math.cos(a), -math.sin(a), 0)
            tc = pc + dv * 0.74 + V(0, 0, 0.20)
            ctx.part(blob(f"{T} {leg} toe {s}{k}", tc, (0.21, 0.40, 0.20), [M["iron"]], 16, 10, power=2.6,
                          frame=Matrix((sv, dv, V(0, 0, 1))).transposed(), tile=0.5), rigid(ft))
            ctx.part(trim(f"{T} {leg} toe band {s}{k}", ring_points(tc + dv * 0.20 + V(0, 0, 0.032), dv, 0.200, 14), 0.028, M["trim"],
                          closed=True), rigid(ft))
            cb = tc + dv * 0.34 + V(0, 0, 0.02)
            ctx.part(spike(f"{T} {leg} claw {s}{k}", cb, cb + dv * 0.50 + V(0, 0, -0.17), 0.155, [M["dark"]], sides=6,
                           bend=0.13), rigid(ft))
            ctx.part(trim(f"{T} {leg} claw ferrule {s}{k}", ring_points(cb + dv * 0.09 + V(0, 0, -0.01), dv, 0.15, 12), 0.03,
                          M["trim"], closed=True), rigid(ft))
        for k in (-1, 1):
            a = math.pi + k * 0.55
            b = pc + V(math.sin(a) * 0.56, math.cos(a) * 0.56, 0.24)
            ctx.part(spike(f"{T} {leg} heel spur {s}{k}", b, b + V(math.sin(a) * 0.22, math.cos(a) * 0.28, 0.12), 0.095,
                           [M["dark"]], sides=5), rigid(ft))


# ===== 裙甲 =====
SKIRT_Y = [0.50, -0.05, -0.60, -1.12]
SKIRT_W = 0.25


def skirt_frame(y, sd):
    top = hull(y, sd * 2.02, 0.07)
    ya = V(sd * 0.20, 0, -1).normalized()
    return top, V(0, 1, 0), ya


def build_skirts(ctx, M):
    T = ctx.title
    for sd, s in SIDES:
        for k, y in enumerate(SKIRT_Y):
            top, xa, ya = skirt_frame(y, sd)
            W = SKIRT_W
            outline = [(-W, 0.0), (W, 0.0), (W, 0.74), (W * 0.5, 0.90), (0.0, 0.82), (-W * 0.5, 0.90), (-W, 0.74)]
            bone = f"Skirt{k}.{s}"
            na = xa.cross(ya).normalized()
            og = -sd                                    # plate 法向 na 恒朝 -X，乘 og 后朝外
            bulge = lambda x, yy, og=og: 0.055 * (1 - (x / SKIRT_W) ** 2) * og   # noqa: E731
            ctx.part(plate(f"{T} skirt {s}{k}", outline, 0.04, [M["plate"]], origin=top, xaxis=xa, yaxis=ya, bulge=bulge,
                           bev=0.008), rigid(bone))
            off = lambda x, yy, top=top, na=na, og=og, bulge=bulge: \
                top + xa * x + ya * yy + na * (bulge(x, yy) + 0.030 * og)   # noqa: E731
            edge = [off(x, yy) for x, yy in outline]
            ctx.part(trim(f"{T} skirt trim {s}{k}", edge, 0.024, M["trim"], closed=True), rigid(bone))
            ctx.part(trim(f"{T} skirt rib {s}{k}", [off(0, 0.06 + 0.64 * q / 6) for q in range(7)], 0.022, M["brass"]), rigid(bone))
            items = [(off(x * 0.8, yy), na * og, 0.030) for x, yy in
                     ((-W, 0.1), (W, 0.1), (-W, 0.40), (W, 0.40), (-W, 0.66), (W, 0.66))]
            ctx.part(studs(f"{T} skirt rivets {s}{k}", items, [M["brass"]]), rigid(bone))
            ctx.part(gem(f"{T} skirt lamp {s}{k}", off(0, 0.50) + V(sd * 0.08, 0, 0), 0.07, M["glow"], (0.6, 1, 1)),
                     rigid(bone))
        hinge = [skirt_frame(y, sd)[0] + V(sd * 0.02, 0, 0.0) for y in (0.80, 0.50, -0.05, -0.60, -1.12, -1.40)]
        ctx.part(tube(f"{T} skirt hinge {s}", hinge, [0.045] * 6, [M["dark"]], n=8, per=2), fn(torso_w))


# ===== 尾锤 =====
TAIL = [V(*p) for p in ((0, -2.85, 2.66), (0, -3.30, 2.58), (0, -3.65, 2.30), (0, -3.85, 1.92), (0, -3.92, 1.52))]


def build_tail(ctx, M):
    T = ctx.title
    for j in range(4):
        a, b = TAIL[j], TAIL[j + 1]
        r0 = 0.38 - 0.05 * j
        ctx.part(sweep(f"{T} tail seg {j}", [a, a.lerp(b, 0.5), b], [r0, r0 * 0.95, r0 * 0.86], [M["plate"]], n=18, per=2,
                       tile=0.6), rigid(f"Tail0.{j + 1}"))
        d = (b - a).normalized()
        ctx.part(trim(f"{T} tail band {j}", ring_points(a.lerp(b, 0.12), d, r0 * 1.06, 18), 0.032, M["trim"], closed=True),
                 rigid(f"Tail0.{j + 1}"))
        ctx.part(spike(f"{T} tail spike {j}", a.lerp(b, 0.5) + V(0, 0, r0 * 0.9),
                       a.lerp(b, 0.5) + V(0, -0.12, r0 + 0.26), 0.055, [M["iron"]], sides=5), rigid(f"Tail0.{j + 1}"))
    c = TAIL[-1] + V(0, -0.05, -0.14)
    ctx.part(blob(f"{T} tail mace", c, (0.44, 0.44, 0.46), [M["iron"]], 24, 14, power=2.4, tile=0.6), rigid("Tail0.4"))
    items = []
    for k in range(14):
        z = 1 - 2 * (k + 0.5) / 14
        r = math.sqrt(max(0.0, 1 - z * z))
        a = k * 2.399
        d = V(math.cos(a) * r, math.sin(a) * r, z)
        items.append((c + d * 0.36, c + d * 0.76, 0.085))
    ctx.part(shards(f"{T} mace spikes", items, [M["trim"]], sides=5), rigid("Tail0.4"))
    ctx.part(trim(f"{T} mace glow ring", ring_points(c, (0, 0, 1), 0.45, 24), 0.028, M["glow"], closed=True), rigid("Tail0.4"))


# ===== 构建 =====
def shift_new(ctx, n0p, n0a, dz):
    """把 n0p / n0a 之后新建的部件整体上移 dz（网格数据不动，改物体位置；节点原点同样上移）。"""
    v = Vector((0, 0, dz))
    for o in [o for o, _ in ctx.parts[n0p:]] + [o for o, *_ in ctx.attached[n0a:]]:
        o.location = o.location + v


def build(ctx):
    M = materials(ctx)
    legs = leg_joints()
    n0p, n0a = len(ctx.parts), len(ctx.attached)
    build_hull(ctx, M)
    build_carapace(ctx, M)
    build_flank(ctx, M)
    build_pipes(ctx, M)
    build_furnace(ctx, M)
    build_neck(ctx, M)
    build_frill(ctx, M)
    h0p, h0a = len(ctx.parts), len(ctx.attached)
    build_head(ctx, M)
    scale_new(ctx, h0p, h0a, HB, HS)
    build_turret(ctx, M)
    build_stacks(ctx, M)
    build_skirts(ctx, M)
    build_tail(ctx, M)
    shift_new(ctx, n0p, n0a, ZB)
    build_pauldrons(ctx, M, legs)
    build_legs(ctx, M, legs)
    bbox_report(ctx.id, [o for o, _ in ctx.parts] + [o for o, *_ in ctx.attached])
    P2.tris_report(ctx, GAME_TRIS, LOD_KEEP)
    return {"legs": legs}


# ===== 骨骼 =====
def skeleton(rig, st):
    Zb = V(0, 0, ZB)                              # 上身骨整体上移 ZB（与 shift_new 一致）
    rig.bone("Root", (0, 0, 0), (0, 0, 0.5))
    rig.bone("Hover", (0, 0, 0.5), (0, 0, 1.0), "Root")
    rig.translate["Hover"] = "_hover"
    rig.bone("Rump", V(0, -1.95, 2.50) + Zb, V(0, -0.5, 2.62) + Zb, "Hover", roll=Z)
    rig.bone("Spine", V(0, -0.5, 2.62) + Zb, V(0, 1.0, 2.70) + Zb, "Rump", roll=Z)
    rig.bone("Chest", V(0, 1.0, 2.70) + Zb, V(0, 2.3, 2.62) + Zb, "Spine", roll=Z)
    rig.bone("Neck", V(0, 2.3, 2.62) + Zb, V(0, 3.10, 2.65) + Zb, "Chest", roll=Z)
    hb, f, u, s = head_frame()
    rig.bone("Head", hb + Zb, hs(hb + f * HL) + Zb, "Neck", roll=u)
    hinge = hb - f * 0.25 + f * 0.34 - u * 0.30
    rig.bone("Jaw", hs(hinge) + Zb, hs(hinge + f * 1.0) + Zb, "Head", roll=u)
    rig.bone("Turret", T_PIVOT + Zb, T_PIVOT + V(0, 0, 0.6) + Zb, "Spine", roll=Y)
    rig.bone("Cannon", TRUNNION + Zb, TRUNNION + V(0, 0.6, 0) + Zb, "Turret", roll=Z)
    rig.bone("Barrel", TRUNNION + V(0, 0.1, 0) + Zb, TRUNNION + V(0, 2.8, 0) + Zb, "Cannon", roll=Z)
    rig.translate["Barrel"] = "_recoil"
    rig.bone("Muzzle", MUZZLE + Zb, MUZZLE + V(0, 0.5, 0) + Zb, "Barrel", roll=Z)
    for (leg, s_), L in st["legs"].items():
        up, lo, ft = f"{leg}Up.{s_}", f"{leg}Low.{s_}", f"{leg}Foot.{s_}"
        rig.bone(up, L["top"], L["mid"], L["parent"], roll=L["pole"])
        rig.bone(lo, L["mid"], L["ankle"], up, roll=L["pole"])
        rig.bone(ft, L["ankle"], L["toe"], lo, roll=Z)
        for a_k, b_k, pn, qn in (("pa", "pb", "A", "B"), ("pc", "pd", "C", "D")):
            dd = (L[b_k] - L[a_k]).normalized()
            rig.bone(f"{leg}Piston{pn}.{s_}", L[a_k], L[a_k] + dd * 0.3, up, roll=V(L["sd"], 0, 0))
            rig.bone(f"{leg}Piston{qn}.{s_}", L[b_k], L[b_k] - dd * 0.3, lo, roll=V(L["sd"], 0, 0))
    prev = "Rump"
    for j in range(4):
        rig.bone(f"Tail0.{j + 1}", TAIL[j] + Zb, TAIL[j + 1] + Zb, prev, roll=Z)
        prev = f"Tail0.{j + 1}"
    for sd, s_ in SIDES:
        for k, y in enumerate(SKIRT_Y):
            top, xa, ya = skirt_frame(y, sd)
            rig.bone(f"Skirt{k}.{s_}", top + Zb, top + ya * 0.7 + Zb, torso_bone(y), roll=V(sd, 0, 0))
    for (sd, s_), top in zip(SIDES, STACKS):
        rig.bone(f"Stack.{s_}", top + Zb, top + V(0, 0, 0.4) + Zb, "Rump", roll=Y)
    for (sd, s_), mouth in zip(SIDES, VENTS):
        rig.bone(f"Vent.{s_}", mouth + Zb, mouth + V(0, 0, 0.4) + Zb, "Chest", roll=Y)
    register_chains(rig, "Tail", 1, 4)
    rig.scaled = ["Stack.L", "Stack.R", "Vent.L", "Vent.R", "Muzzle"]


# ===== 动作工具 =====
def impact(d, w=0.06):
    """落脚冲击脉冲（d 为距落脚的周期相位）。"""
    d = d - 0.02
    return math.exp(-(d / w) ** 2) + math.exp(-((d - 1) / w) ** 2) + math.exp(-((d + 1) / w) ** 2)


def pad_points(L):
    pc = Vector((L["ankle"].x, L["ankle"].y + 0.06, 0.0))
    pts = [pc + Vector((math.sin(a) * PAD_R, math.cos(a) * PAD_R, 0.03)) for a in [q / 8 * TAU for q in range(8)]]
    pts += [pc + Vector((math.sin(a) * 1.28, math.cos(a) * 1.28, 0.05)) for a in (-0.72, 0.0, 0.72)]   # 爪尖
    return pts


def pad_low(rig, st, pose, key):
    leg, s = key
    name = f"{leg}Foot.{s}"
    h0 = rig.SEG[name][0]
    h = rig.head(pose, name)
    d = rig.delta(pose, name)
    return min((h + d @ (p - h0)).z for p in st["pads"][key])


def rot_x(v, a):
    return Matrix.Rotation(a, 3, "X") @ Vector(v)


def plant_legs(rig, st, p, feet):
    """feet: {(腿, 侧): (踝目标, 脚俯仰, 离地权重 air, 身体系收腿目标或 None)}。"""
    for key, (target, pitch, air, local) in feet.items():
        leg, s = key
        L = st["legs"][key]
        par = L["parent"]
        D = rig.delta(p, par)
        pole = D @ L["pole"]
        tgt = Vector(target)
        fdir = rot_x(L["foot_dir"], pitch)
        if air > 0 and local is not None:
            top = rig.head(p, f"{leg}Up.{s}")
            body_t = top + D @ Vector(local[0])
            tgt = tgt.lerp(body_t, air)
            fdir = fdir.lerp(D @ rot_x(L["foot_dir"], local[1]), air).normalized()
        rig.ik2(p, f"{leg}Up.{s}", f"{leg}Low.{s}", tgt, pole, end=f"{leg}Foot.{s}", end_dir=fdir, end_up=Z,
                rest_pole=L["pole"])


def pistons(rig, p):
    for leg in ("Fore", "Hind"):
        for _, s in SIDES:
            for pn, qn in (("A", "B"), ("C", "D")):
                a, b = f"{leg}Piston{pn}.{s}", f"{leg}Piston{qn}.{s}"
                ha, hb = rig.head(p, a), rig.head(p, b)
                rig.aim(p, a, hb - ha)
                rig.aim(p, b, ha - hb)


def exhaust(rig, p, t, stack=0.6, vent=0.5, muzzle=0.0, flicker=0.12, drift=(0.0, 0.0)):
    sc = {}
    for k, (_, s) in enumerate(SIDES):
        sc[f"Stack.{s}"] = max(0.02, 0.72 * stack * (1 + flicker * math.sin(3 * t + k * 1.9)))
        sc[f"Vent.{s}"] = max(0.02, 0.72 * vent * (1 + flicker * math.sin(4 * t + k * 2.3 + 1)))
        rig.aim(p, f"Stack.{s}", Vector((drift[0] + 0.05 * math.sin(2 * t + k), drift[1] + 0.05 * math.cos(2 * t + k), 1)))
        rig.aim(p, f"Vent.{s}", Vector((drift[0] + (0.25 if s == "R" else -0.25), drift[1] - 0.15, 1)))
    sc["Muzzle"] = max(0.01, muzzle)
    p["_scale"] = sc


def rest_feet(st):
    return {key: (L["ankle"].copy(), 0.0, 0.0, None) for key, L in st["legs"].items()}


BASE = {"x": 0.0, "y": 0.0, "z": 0.0, "rear": 0.0, "roll": 0.0, "yaw": 0.0, "bend": 0.0, "chest": 0.0, "neck": 0.0,
        "nyaw": 0.0, "head": 0.0, "hyaw": 0.0, "shake": 0.0, "jaw": 0.03, "turret": 0.0, "gun": 0.0, "recoil": 0.0,
        "tail": 0.0, "tyaw": 0.0, "skirt": 0.04, "stack": 0.6, "vent": 0.5, "muzzle": 0.0, "air": 0.0, "paw": 0.0}


def pose_from(rig, st, q, feet, t=0.0):
    """由参数生成姿态：x/y/z 身体位移、rear 以后髋为轴的人立角、roll/yaw 身体侧滚与偏航、bend 腰背弯、
    neck/head 颈与头俯仰、jaw 张颚、turret/gun 炮塔偏航与炮管俯仰、recoil 后坐、tail 尾巴上卷、
    skirt 裙甲外摆、stack/vent/muzzle 火焰倍率、air 前腿离地权重、paw 刨蹄相位。"""
    p = {}
    p["_hover"] = Vector((q["x"], q["y"], q["z"]))
    p["Rump"] = R((X, q["rear"]), (Y, q["roll"]), (Z, q["yaw"]))
    p["Spine"] = R((X, q["bend"] * 0.5), (Y, -q["roll"] * 0.4))
    p["Chest"] = R((X, q["bend"] * 0.5 + q["chest"]), (Y, -q["roll"] * 0.4))
    p["Neck"] = R((X, q["neck"]), (Z, q["nyaw"]))
    p["Head"] = R((X, q["head"]), (Z, q["hyaw"]), (Y, q["shake"]))
    p["Jaw"] = R((X, -q["jaw"]))
    p["Turret"] = R((Z, q["turret"]))
    p["Cannon"] = R((X, q["gun"]))
    p["_recoil"] = Vector((0, -q["recoil"], 0))
    for j in range(4):
        p[f"Tail0.{j + 1}"] = R((Z, q["tyaw"] * (0.6 + 0.3 * j) + 0.10 * math.sin(t - j * 0.7) * 0.3),
                                (X, -q["tail"] * (0.55 - 0.08 * j)))
    for sd, s in SIDES:
        for k in range(len(SKIRT_Y)):
            sw = q["skirt"] + 0.03 * math.sin(2 * t + k * 0.9 + (sd + 1))
            p[f"Skirt{k}.{s}"] = R((Y, -sd * sw), (X, 0.04 * math.sin(2 * t + k)))
    feet = dict(feet)
    for sd, s in SIDES:
        key = ("Fore", s)
        tgt, pitch, _, _ = feet[key]
        if q["air"] > 0:
            ph = q["paw"] + (0 if s == "L" else math.pi)
            local = (Vector((0.0, 0.55 + 0.35 * math.sin(ph), -1.30 + 0.28 * math.cos(ph))), -0.9 + 0.3 * math.sin(ph))
            feet[key] = (tgt, pitch, q["air"], local)
    plant_legs(rig, st, p, feet)
    pistons(rig, p)
    exhaust(rig, p, t, q["stack"], q["vent"], q["muzzle"])
    return p


# ===== 各动作 =====
def idle_pose(rig, st, t):
    q = dict(BASE)
    q["z"] = -0.02 + 0.025 * math.sin(t)
    q["roll"] = 0.012 * math.sin(t)
    q["bend"] = 0.012 * math.sin(t + 0.5)
    q["neck"] = -0.03 + 0.03 * math.sin(t + 0.9)
    q["head"] = 0.02 * math.sin(t + 1.4)
    q["hyaw"] = 0.08 * math.sin(t)
    q["jaw"] = 0.04 + 0.03 * math.sin(2 * t)
    q["turret"] = 0.30 * math.sin(t)
    q["gun"] = 0.04 * math.sin(2 * t)
    q["tyaw"] = 0.10 * math.sin(t + 0.5)
    q["stack"] = 0.55 + 0.12 * math.sin(2 * t)
    q["vent"] = 0.35 + 0.10 * math.sin(2 * t + 1)
    return pose_from(rig, st, q, rest_feet(st), t * 2)


PHASE = {("Hind", "L"): 0.0, ("Fore", "L"): 0.25, ("Hind", "R"): 0.5, ("Fore", "R"): 0.75}


def walk_feet(st, t, stride=1.05, lift=0.34, duty=0.72):
    feet, shock = {}, 0.0
    for key, ph in PHASE.items():
        L = st["legs"][key]
        c = (t / TAU + ph) % 1.0
        if c < duty:
            s_ = c / duty
            dy, dz, pitch = stride * (0.5 - s_), 0.0, 0.0
        else:
            s_ = (c - duty) / (1 - duty)
            e = ease_io(s_)
            dy = stride * (-0.5 + e)
            dz = lift * math.sin(math.pi * s_) ** 0.8
            pitch = 0.30 * math.sin(math.pi * s_) - 0.12 * math.sin(math.pi * s_) ** 4
        shock += impact(c)
        feet[key] = (L["ankle"] + Vector((0, dy, dz)), pitch, 0.0, None)
    return feet, shock


def move_pose(rig, st, t):
    feet, shock = walk_feet(st, t)
    q = dict(BASE)
    q["x"] = 0.05 * math.sin(t - 0.3)
    q["z"] = -0.06 - 0.035 * shock + 0.02 * math.cos(2 * t)
    q["roll"] = 0.035 * math.sin(t - 0.3)
    q["yaw"] = 0.03 * math.sin(t)
    q["bend"] = 0.02 * math.sin(2 * t)
    q["neck"] = -0.06 + 0.05 * math.sin(2 * t + 0.6)
    q["head"] = -0.02 + 0.04 * math.sin(2 * t + 1.2)
    q["hyaw"] = -0.05 * math.sin(t)
    q["shake"] = 0.02 * math.sin(t + 0.4)
    q["jaw"] = 0.05
    q["turret"] = 0.12 * math.sin(t)
    q["gun"] = 0.03 * math.sin(2 * t)
    q["tyaw"] = -0.18 * math.sin(t - 0.8)
    q["tail"] = 0.08
    q["skirt"] = 0.06 + 0.04 * shock
    q["stack"] = 0.65 + 0.30 * shock
    q["vent"] = 0.45 + 0.2 * shock
    return pose_from(rig, st, q, feet, t * 2)


def step_track(steps, f):
    """落步轨道：steps 为 [(起帧, 止帧, 起点偏移, 终点偏移, 抬高)]，返回 (dy, dz, pitch)。"""
    dy = steps[0][2]
    for f0, f1, d0, d1, h in steps:
        if f < f0:
            break
        if f <= f1:
            s_ = (f - f0) / (f1 - f0)
            return lerp(d0, d1, ease_io(s_)), h * math.sin(math.pi * s_), 0.35 * math.sin(math.pi * s_)
        dy = d1
    return dy, 0.0, 0.0


def attack_keys():
    """冲锋撞角：1 → 9 后缩蓄力（压低头、角朝前）→ 14 前冲（前蹄跨步落地）→ 16 撞击上挑 → 21 顿住喷气 →
    30 退回原位 → 33 收势。"""
    coil = {"y": -0.45, "z": -0.18, "rear": -0.06, "chest": -0.04, "neck": -0.26, "head": -0.14, "jaw": 0.0,
            "tail": 0.25, "stack": 1.0, "vent": 0.8, "skirt": 0.02, "turret": 0.0, "gun": -0.05}
    charge = {"y": 0.85, "z": -0.06, "rear": -0.08, "chest": -0.06, "neck": -0.36, "head": -0.08, "jaw": 0.10,
              "tail": 0.45, "tyaw": 0.0, "stack": 1.7, "vent": 1.5, "skirt": 0.16, "gun": -0.10}
    hook = dict(charge, y=0.95, z=0.02, rear=-0.02, neck=-0.12, head=0.30, jaw=0.35, stack=2.0, vent=1.8,
                skirt=0.22, shake=0.04)
    hold = dict(hook, y=0.88, neck=-0.16, head=0.18, jaw=0.25, stack=1.5, vent=1.3, shake=-0.03, skirt=0.10)
    back = dict(BASE, y=0.30, neck=-0.08, head=0.04, stack=0.9, vent=0.7, tail=0.1)
    return with_defaults(BASE, [(1, {}, "io"), (9, coil, "io"), (14, charge, "in"), (16, hook, "out"),
                                (21, hold, "io"), (27, back, "io"), (33, {}, "io")])


ATTACK_STEPS = {"Fore": [(8, 14, 0.0, 0.90, 0.36), (24, 31, 0.90, 0.0, 0.28)],
                "Hind": [(10, 15, 0.0, 0.45, 0.24), (26, 32, 0.45, 0.0, 0.20)]}


def attack_feet(st, f):
    feet = {}
    for key, L in st["legs"].items():
        leg, s = key
        lag = 0 if s == "L" else 1                     # 左右错开一帧，免得像并腿跳
        dy, dz, pitch = step_track([(a + lag, b + lag, c, d, h) for a, b, c, d, h in ATTACK_STEPS[leg]], f)
        feet[key] = (L["ankle"] + Vector((0, dy, dz)), pitch, 0.0, None)
    return feet


def enrage_keys():
    """人立咆哮：1 → 8 下伏蓄力（火焰内敛）→ 18 后腿人立、前蹄离地刨空、仰头张颚、所有排气口爆燃、炮口朝天 →
    22 / 28 两次开炮（后坐 + 炮口焰）→ 33 保持 → 37 砸落前蹄 → 42 余震 → 49 收势。"""
    crouch = {"y": 0.10, "z": -0.22, "rear": -0.07, "neck": -0.30, "head": -0.10, "tail": 0.2, "stack": 0.35,
              "vent": 0.25, "skirt": 0.0}
    # 开炮时炮塔朝正前（炮口随人立朝天），打完两炮后炮塔甩一整圈
    rear = {"y": -0.35, "z": -0.22, "rear": 0.60, "chest": -0.06, "bend": 0.05, "neck": 0.32, "head": 0.32,
            "jaw": 0.55, "tail": 0.85, "stack": 2.3, "vent": 2.1, "skirt": 0.30, "air": 1.0, "paw": 0.0,
            "turret": 0.0, "gun": 0.40}
    rear2 = dict(rear, rear=0.64, head=0.38, jaw=0.65, paw=2.6, stack=2.5, vent=2.3)
    rear3 = dict(rear2, rear=0.58, paw=5.2, turret=0.9, head=0.30)
    drop = dict(BASE, y=0.05, z=-0.26, rear=-0.06, neck=-0.18, head=-0.12, jaw=0.40, tail=0.3, stack=2.0, vent=1.8,
                skirt=0.28, turret=3.3, gun=0.05, shake=0.05)
    settle = dict(BASE, z=-0.08, turret=TAU - 0.5, stack=1.0, vent=0.8, jaw=0.12, skirt=0.08)
    end = dict(BASE, turret=TAU)
    return with_defaults(BASE, [(1, {}, "io"), (8, crouch, "io"), (18, rear, "out"), (26, rear2, "lin"),
                                (33, rear3, "lin"), (37, drop, "in"), (42, settle, "out"), (49, end, "io")])


def shot(f, f0):
    """开炮：炮口焰在 f0 爆开、3 帧内收回；后坐在 f0 瞬间到位、6 帧回弹。"""
    d = f - f0
    flash = 0.0 if d < 0 else math.exp(-d / 1.3) * 1.6 if d < 4 else 0.0
    recoil = 0.0 if d < 0 else 0.38 * math.exp(-d / 2.2) if d < 9 else 0.0
    return flash, recoil


def animate(rig, st):
    st["pads"] = {key: pad_points(L) for key, L in st["legs"].items()}
    lows = {c: (9.0, 0) for c in CLIPS}

    def rec(clip, fr, p):
        lo = min(pad_low(rig, st, p, key) for key in st["legs"])
        if lo < lows[clip][0]:
            lows[clip] = (lo, fr)
        return p
    loop(rig, "Idle", 96, lambda t: rec("Idle", t, idle_pose(rig, st, t)), step=2)
    loop(rig, "Move", 48, lambda t: rec("Move", t, move_pose(rig, st, t)), step=1)
    ak = attack_keys()

    def attack(f):
        q = track(ak, f)
        return rec("Attack", f, pose_from(rig, st, q, attack_feet(st, f), f * 0.5))
    sampled(rig, "Attack", 32, attack)
    ek = enrage_keys()

    def enrage(f):
        q = track(ek, f)
        if 18 <= f <= 36:                                # 人立时的震颤
            amp = smoothstep(18, 20, f) * (1 - smoothstep(32, 36, f))
            q["shake"] += 0.04 * math.sin(f * 2.2) * amp
            q["rear"] += 0.015 * math.sin(f * 1.6) * amp
        fl, rc = 0.0, 0.0
        for f0 in (22, 28):
            a, b = shot(f, f0)
            fl, rc = max(fl, a), max(rc, b)
        q["muzzle"], q["recoil"] = fl, rc
        return rec("Enrage", f, pose_from(rig, st, q, rest_feet(st), f * 0.8))
    sampled(rig, "Enrage", 48, enrage)
    for clip in CLIPS:
        print(f"MOTION CHECK+ {clip}: lowest foot pad point {lows[clip][0]:.3f} m")
    tail_check(rig)
    seam_check(rig, ("Idle", "Move"))


def tail_check(rig):
    """尾锤离地：Tail0.4 末端减去锤头半径。"""
    import bpy
    scene = bpy.context.scene
    for clip in CLIPS:
        act = bpy.data.actions[clip]
        rig.obj.animation_data.action = act
        f0, f1 = map(int, act.frame_range)
        lo = (9.0, 0)
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            z = rig.obj.pose.bones["Tail0.4"].tail.z - 0.75
            if z < lo[0]:
                lo = (z, f)
        print(f"MOTION CHECK+ {clip}: min tail mace clearance {lo[0]:.3f} m at frame {lo[1]}")
