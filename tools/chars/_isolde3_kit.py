"""伊索尔德第三轮返工的私有辅助：有体量的分层甲片（尖角下缘 + 凸棱 + 浮雕霜纹）、浮雕冰白漆甲贴图、
加厚的腿甲 / 臂甲 / 护手 / 躯干甲、低面数内衬、滑冰步态 2.0。

只被 tools/chars/isolde.py 引用；不改 tools/kit/ 与 _grace_helpers.py。
上一轮的 _isolde2_kit 仍提供刻面冰晶、贴图、处刑大剑、大衣让腿等。
"""

import math

import numpy as np
from mathutils import Vector

from kit.core import (TAU, Canvas, apply_all, axis_ref, box_blur, chain, clamp, ellipsoid, finish, height_normal, invdist,
                      lerp, orient, plate, radial, rigid, smoothstep, solidify, subsurf, surface, trim, tube)
from nyx_lib import bevel
from kit.humanoid import limb_frame, SIDES
from kit.motion import Legs
from kit.rig import R, X, Y, Z

from chars._grace_helpers import cyc_hermite
from chars._isolde2_kit import SKATE2, ON_ICE2, arm_dir, crystal2


def finish3(obj, thick, bev=0.0):
    """加厚 + 单段倒角（kit.finish 的倒角固定 2 段，板边一圈面数翻倍；1 段倒角足够吃出板边高光）并应用。"""
    solidify(obj, thick, 1, 0, 0)
    if bev:
        bevel(obj, bev, 1, 30)
    return apply_all(obj)


# ===== 低面数内衬（大多被甲片盖住，不值得花面数） =====
def suit_torso2(ctx, B, mat, nu=22, nv=16):
    """躯干内衬：不细分、分段少（上一轮 28×22 + 细分一级，大半在甲下）。"""
    z0, z1 = B.torso[-1][0], B.torso[0][0]
    body = surface(f"{ctx.title} torso", lambda u, v: B.torso_point(u * TAU, lerp(z0, z1, v), 0.0), nu, nv, [mat],
                   closed_u=True)
    orient(body, lambda c: Vector((0, 0, c.z)))
    ctx.part(apply_all(body), invdist(["Pelvis", "Spine", "Chest", "Neck"]))
    neck = tube(f"{ctx.title} neck", [(0, 0, B.neck_base - 0.02 * B.s), (0, 0.006 * B.s, B.chin),
                                      (0, 0.012 * B.s, B.chin + 0.06 * B.s)],
                [0.052 * B.s, 0.044 * B.s, 0.042 * B.s], [mat], n=12, per=2)
    ctx.part(neck, invdist(["Chest", "Neck", "Head"]))


def suit_arm2(ctx, B, label, mat, r=(0.050, 0.054, 0.047, 0.040, 0.031)):
    a = B.arms[label]
    s = B.s * B.limb
    mid = (a["shoulder"] + a["elbow"]) / 2
    arm = tube(f"{ctx.title} arm {label}", [a["inner"], a["shoulder"], mid, a["elbow"], a["wrist"]],
               [x * s for x in r], [mat], n=10, per=3)
    ctx.part(arm, chain([f"UpperArm.{label}", f"Forearm.{label}", f"Hand.{label}"], "Chest", 0.05))


def suit_leg2(ctx, B, label, mat, r=(0.088, 0.080, 0.062, 0.060, 0.050, 0.040)):
    L = B.legs[label]
    s = B.s * B.limb
    hip, knee, ankle = L["hip"], L["knee"], L["ankle"]
    top = hip + Vector((0, 0, 0.05 * B.s))
    pts = [top, hip.lerp(knee, 0.35), knee, knee.lerp(ankle, 0.3), knee.lerp(ankle, 0.7), ankle]
    leg = tube(f"{ctx.title} leg {label}", pts, [x * s for x in r], [mat], n=12, per=3)
    ctx.part(leg, chain([f"Thigh.{label}", f"Shin.{label}", f"Foot.{label}"], "Pelvis", 0.06))


# ===== 分层甲片 =====
def band3(ctx, name, a, b, r0, r1, mat, spec, out, closed=False, arc=1.75, v0=0.0, v1=1.0, bulge=0.0, ridge=0.0,
          flare0=0.0, flare1=0.0, drop=0.0, flutes=0, amp=0.0, thick=0.005, nu=22, nv=7, trim_mat=None,
          trim_r=0.0022, rims=(1,), rim_n=20, rim_sides=3, lift=1.0, scale_v=None):
    """包裹肢体段 a→b 的弧形 / 整圈甲片（改写自 limb_plate）：
    drop 让下缘在中线处向下伸出成尖角（花剑式甲片下缘）；flutes/amp 在弧面上压出竖向凸棱；
    滚边点数与边数可控。返回 (pt, outer)：pt 为内表面点，outer(u, v, lift) 为外表面点（给浮雕霜纹用）。"""
    axis, o, w = limb_frame(a, b, out)
    L = (b - a).length

    def edge(th):
        if not drop:
            return 0.0
        if closed:
            return drop * (0.5 + 0.5 * math.cos(th)) ** 2.2
        return drop * max(0.0, 1 - abs(th) / arc) ** 1.4

    def pt(u, v):
        th = (2 * u - 1) * arc if not closed else u * TAU
        t = lerp(v0, v1 + edge(th) / L, v)
        c = a.lerp(b, t)
        r = (lerp(r0, r1, v) + bulge * math.sin(v * math.pi) + ridge * math.exp(-(th / 0.28) ** 2)
             + flare0 * (1 - smoothstep(0.0, 0.18, v)) + flare1 * smoothstep(0.82, 1.0, v))
        if flutes:
            r += amp * (0.5 + 0.5 * math.cos(flutes * th))
        return c + (o * math.cos(th) + w * math.sin(th)) * r

    def rad(p):
        q = a + axis * (p - a).dot(axis)
        d = p - q
        return d.normalized() if d.length > 1e-9 else o

    def outer(u, v, extra=0.0012):
        p = pt(u, v)
        return p + rad(p) * (thick + extra)

    obj = surface(name, pt, nu, nv, [mat], closed_u=closed)
    orient(obj, lambda c: a + axis * (c - a).dot(axis))
    ctx.part(finish3(obj, thick, thick * 0.34), spec)
    if trim_mat:
        for v in rims:
            n = rim_n
            pts = [pt(i / (n if closed else n - 1), v) for i in range(n)]
            pts = [p + rad(p) * thick * lift for p in pts]
            ctx.part(trim(f"{name} rim {v}", pts, trim_r, trim_mat, closed=closed, n=rim_sides), spec)
    return pt, outer


def fern(ctx, outer, spec, mat, name, u_c, v_a, v_b, wu, wv, branches=((0.22, 0.045), (0.42, 0.040), (0.62, 0.033),
                                                                          (0.80, 0.024)),
         ang=52.0, r=0.0022, sides=3):
    """浮雕霜纹：在曲面 outer(u, v) 上贴一根茎 + 成对斜分枝（羽状枝晶），茎、枝都是微微凸起的细管。
    wu / wv 为 u、v 方向一个单位对应的米数，用来把分枝角度换算回真实 60° 左右的枝晶。"""
    a = math.radians(ang)
    stem = [outer(u_c, lerp(v_a, v_b, i / 4)) for i in range(5)]
    ctx.part(tube(f"{name} stem", stem, [r * 1.15, r, r * 0.9, r * 0.7, r * 0.3], [mat], n=sides, per=1, cap=False),
             spec)
    for f, L in branches:
        vb = lerp(v_a, v_b, f)
        for sd in (-1, 1):
            du = sd * L * math.sin(a) / wu
            dv = L * math.cos(a) / wv
            pts = [outer(clamp(u_c + du * t, 0.02, 0.98), clamp(vb + dv * t, 0.02, 0.98)) for t in (0.0, 0.5, 1.0)]
            ctx.part(tube(f"{name} twig {f:.2f}{sd}", pts, [r * 0.9, r * 0.7, r * 0.25], [mat], n=sides, per=1,
                          cap=False), spec)


# ===== 浮雕冰白漆甲贴图 =====
def lacquer_maps(frame_rgb, field_rgb, relief_rgb, groove_rgb, emit_rgb, size=2048, seed=31, border=0.11, cells=3,
                 width=9, corner=0.07):
    """冰白漆甲（每个甲片自带 0–1 UV）：高光白的凸起外框 → 一道细刻线 + 内侧冷光细线 → 淡冰蓝内板，
    内板里的霜星 / 卷草是比内板更亮的“凸起”浮雕（法线向外鼓），旁边落一圈浅蓝阴影，读作浮雕而不是蓝色彩绘。"""
    rng = np.random.default_rng(seed)
    sc = size / 2048
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size

    def box_dist(inset):
        qx = np.abs(xs - 0.5) - (0.5 - inset - corner)
        qy = np.abs(ys - 0.5) - (0.5 - inset - corner)
        out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0)
        return out - corner
    d = box_dist(border)
    px = 1.0 / size
    field = np.clip(-d * size / (10 * sc), 0, 1)                      # 内板：离刻线越远越“满”
    groove = np.clip(1 - np.abs(d + 0.006) / (3.0 * sc * px), 0, 1)
    glow = np.clip(1 - np.abs(d + 0.026) / (2.6 * sc * px), 0, 1)
    cv = Canvas(size, size)
    lo, hi = border + 0.06, 1 - border - 0.06
    cell = (hi - lo) / cells * size
    for gx in range(cells):
        for gy in range(cells):
            cx, cy = lo * size + (gx + 0.5) * cell, lo * size + (gy + 0.5) * cell
            if (gx + gy + int(rng.integers(0, 2))) % 2 == 0:
                r = cell * 0.42
                rot = rng.uniform(0, math.pi / 3)
                for k in range(6):
                    a = rot + k * math.pi / 3
                    cv.line(cx, cy, cx + math.cos(a) * r, cy + math.sin(a) * r, width)
                    for f in (0.46, 0.74):
                        bx, by = cx + math.cos(a) * r * f, cy + math.sin(a) * r * f
                        for sd in (-1, 1):
                            b2 = a + sd * math.pi / 3
                            L = r * (0.34 if f < 0.6 else 0.22)
                            cv.line(bx, by, bx + math.cos(b2) * L, by + math.sin(b2) * L, max(1, width * 2 // 3))
                cv.ring(cx, cy, cell * 0.075, max(1, width * 2 // 3))
            else:
                for sd in (-1, 1):
                    t = np.linspace(0, rng.uniform(1.3, 1.7) * TAU, 90)
                    rr = cell * 0.34 * np.exp(-0.21 * t)
                    ph = rng.uniform(0, TAU)
                    ox = cx + sd * cell * 0.17
                    for i in range(len(t) - 1):
                        cv.line(ox + sd * rr[i] * math.cos(t[i] + ph), cy + rr[i] * math.sin(t[i] + ph),
                                ox + sd * rr[i + 1] * math.cos(t[i + 1] + ph), cy + rr[i + 1] * math.sin(t[i + 1] + ph),
                                max(1, width * 2 // 3))
    eng = np.clip(box_blur(cv.mask, int(2 * sc) + 1) * 1.4, 0, 1) * np.clip(field * 3, 0, 1)
    shade = np.clip(box_blur(np.roll(np.roll(eng, int(7 * sc), axis=0), int(7 * sc), axis=1), int(5 * sc) + 1)
                    * 1.2 - eng, 0, 1)                                  # 浮雕旁的浅阴影
    grain = box_blur(rng.random((size, size)).astype(np.float32), int(26 * sc) + 2) - 0.5
    tone = (1.0 + grain * 0.35)[..., None]
    f3 = field[..., None]
    base = (np.array(frame_rgb) * (1 - f3) + np.array(field_rgb) * f3) * tone
    base = base * (1 - shade[..., None] * 0.30) + np.array(groove_rgb) * (shade[..., None] * 0.30)
    base = base * (1 - eng[..., None] * 0.9) + np.array(relief_rgb) * eng[..., None] * 0.9
    gm = np.clip(groove, 0, 1)[..., None]
    base = base * (1 - gm) + np.array(groove_rgb) * gm
    em = np.stack([(glow * 0.9 + box_blur(glow, int(3 * sc) + 1) * 0.5) * c for c in emit_rgb], axis=2)
    height = 0.55 * (1 - field) + 0.55 * eng - 0.9 * groove
    return (np.clip(base, 0, 1), np.clip(em, 0, 1),
            height_normal(box_blur(height.astype(np.float32), 2), 4.5 * sc))


def coat_maps(emit_rgb, navy, thread_rgb, size=2048, seed=9):
    """深海军蓝大衣：下摆向上生长的霜花（发光）+ 其上渐显的暗纹菱格织锦（衣身上部、袖筒），线色偏冰蓝不发灰。
    贴图第 0 行为下摆：织锦权重随高度由 0 渐增到 1，霜花区干净、上身有织纹。"""
    from chars._grace_helpers import frost_hem_maps
    from chars._isolde2_kit import brocade_maps
    b1, e1, n1 = frost_hem_maps(emit_rgb, navy, line_rgb=(0.06, 0.15, 0.36), size=size, seed=seed, roots=16,
                                reach=0.40, stars=22, width=2, fade=(0.03, 0.40))
    b2, _, n2 = brocade_maps(navy, thread_rgb, size=size // 2, seed=5, cells=22)
    b2 = np.tile(b2, (2, 2, 1))
    n2 = np.tile(n2, (2, 2, 1))
    v = np.linspace(0, 1, size)[:, None, None]
    w = np.clip((v - 0.30) / 0.30, 0, 1)
    base = np.clip(b1 + (b2 - np.array(navy)) * w, 0, 1)
    nrm = n1 * (1 - w) + (0.5 * n1 + 0.5 * n2) * w
    return base, e1, nrm


# ===== 腿甲 =====
def leg_armor3(ctx, B, side, label, M, crystal_mat):
    """加厚腿甲：四片叠压大腿甲（尖角下缘、凸棱、浮雕霜纹）+ 冰晶护膝甲杯 + 三片叠压护胫 + 踝口。
    所有半径按“米”写，已按 limb≈1.16 的粗体量标定。"""
    s = B.s
    L = B.legs[label]
    hip, knee, ankle = L["hip"] + Vector((0, 0, 0.03 * s)), L["knee"], L["ankle"]
    thigh_spec = ("rigid", {f"Thigh.{label}": 1.0})
    shin_spec = ("rigid", {f"Shin.{label}": 1.0})
    knee_spec = ("rigid", {f"Thigh.{label}": 0.5, f"Shin.{label}": 0.5})
    out_t = Vector((side * 0.40, 1, 0))
    tl = (knee - hip).length
    # 大腿：三片叠压，上宽下收，下缘各带一个尖角，外沿一道凸棱
    plan = ((0.00, 0.43, 0.118, 0.112, 0.036), (0.36, 0.73, 0.112, 0.103, 0.030), (0.66, 0.945, 0.103, 0.093, 0.026))
    outers = []
    for k, (v0, v1, r0, r1, dr) in enumerate(plan):
        pt, outer = band3(ctx, f"{ctx.title} cuisse {label}{k}", hip, knee, r0 * s, r1 * s, M["plate"], thigh_spec,
                          out_t, arc=1.85, v0=v0, v1=v1, drop=dr * s, flare1=0.010 * s, ridge=0.011 * s,
                          flutes=3, amp=0.0040 * s, thick=0.0065 * s, nu=22, nv=6, trim_mat=M["silver"],
                          trim_r=0.0034 * s, rims=(0, 1) if k == 0 else (1,), rim_n=22)
        outers.append(outer)
        if k < 2:        # 甲片尖角上凝出的小冰棱（朝下偏外）
            ax_, o_, _w = limb_frame(hip, knee, out_t)
            tip = outer(0.5, 1.0, 0.0)
            d = (-ax_ * 0.85 + o_ * 0.55).normalized()
            ctx.part(crystal2(f"{ctx.title} cuisse tip {label}{k}", tip - d * 0.006 * s, tip + d * 0.050 * s, 0.0085 * s,
                              [crystal_mat], sides=5, shoulder=0.55, foot=0.8, seed=k * 1.7 + side), thigh_spec)
    # 大腿浮雕霜纹：中片与上片各一枝，沿前外侧向下生长
    fern(ctx, outers[0], thigh_spec, M["silver"], f"{ctx.title} cuisse fern {label}0", 0.5, 0.18, 0.86,
         wu=2 * 1.85 * 0.116 * s, wv=0.43 * tl, r=0.0024 * s)
    fern(ctx, outers[1], thigh_spec, M["silver"], f"{ctx.title} cuisse fern {label}1", 0.5, 0.16, 0.80,
         wu=2 * 1.85 * 0.108 * s, wv=0.37 * tl, r=0.0022 * s, branches=((0.25, 0.036), (0.50, 0.030), (0.74, 0.022)))
    axis, o, w = limb_frame(hip, knee, out_t)
    line = [hip.lerp(knee, lerp(0.10, 0.90, i / 12)) + o * (lerp(0.118, 0.094, i / 12) * s + 0.0150 * s)
            for i in range(13)]
    ctx.part(trim(f"{ctx.title} cuisse inlay {label}", line, 0.0020 * s, M["inlay"], n=3), thigh_spec)
    # 护膝：前凸甲杯 + 外侧扇翼 + 三枚放射冰晶 + 上下关节片
    kc = knee + Vector((0, 0.058 * s, 0.006 * s))
    cup = ellipsoid(f"{ctx.title} poleyn {label}", kc, (0.052 * s, 0.038 * s, 0.060 * s), [M["plate"]], 16, 10)
    ctx.part(cup, knee_spec)
    rim = [kc + Vector((math.sin(t) * 0.050 * s, 0.014 * s + 0.008 * s * math.cos(t) ** 2, math.cos(t) * 0.058 * s))
           for t in [i / 22 * TAU for i in range(22)]]
    ctx.part(trim(f"{ctx.title} poleyn rim {label}", rim, 0.0026 * s, M["silver"], closed=True, n=3), knee_spec)
    wing = [kc + Vector((side * 0.034 * s, -0.010 * s, 0.044 * s)), kc + Vector((side * 0.088 * s, -0.034 * s, 0.004 * s)),
            kc + Vector((side * 0.034 * s, -0.012 * s, -0.044 * s))]
    ctx.part(tube(f"{ctx.title} poleyn wing {label}", wing, [0.011 * s, 0.024 * s, 0.011 * s], [M["plate"]], n=6,
                  fx=0.30, up=(side, 0, 0), per=3), knee_spec)
    ctx.part(trim(f"{ctx.title} poleyn wing rim {label}", [p + Vector((side * 0.005 * s, 0.006 * s, 0)) for p in wing],
                  0.0022 * s, M["silver"], n=3, per=2), knee_spec)
    for pos, nm in ((0.88, "top"), (0.0, "low")):
        if nm == "top":
            band3(ctx, f"{ctx.title} knee lame top {label}", hip, knee, 0.094 * s, 0.092 * s, M["plate"], thigh_spec,
                  Vector((side * 0.2, 1, 0)), arc=1.3, v0=0.90, v1=0.99, thick=0.0055 * s, nu=14, nv=3,
                  trim_mat=M["silver"], trim_r=0.0020 * s, rims=(0,), rim_n=12)
        else:
            band3(ctx, f"{ctx.title} knee lame low {label}", knee, ankle, 0.082 * s, 0.080 * s, M["plate"], shin_spec,
                  Vector((side * 0.2, 1, 0)), arc=1.3, v0=0.03, v1=0.12, thick=0.0055 * s, nu=14, nv=3,
                  trim_mat=M["silver"], trim_r=0.0020 * s, rims=(1,), rim_n=12)
    for k, (dx, dz, L_, r) in enumerate(((0.0, 1.0, 0.085, 0.014), (side * 0.78, 0.50, 0.050, 0.010),
                                          (-side * 0.60, 0.62, 0.040, 0.009))):
        d = Vector((dx, 0.50, dz)).normalized()
        b0 = kc + Vector((dx * 0.022 * s, 0.026 * s, dz * 0.034 * s))
        ctx.part(crystal2(f"{ctx.title} knee crystal {label}{k}", b0 - d * 0.008 * s, b0 + d * L_ * s, r * s,
                          [crystal_mat], sides=5, shoulder=0.6, foot=0.6, seed=k * 2.3 + side), knee_spec)
    ctx.part(ellipsoid(f"{ctx.title} knee gem {label}", kc + Vector((0, 0.037 * s, -0.008 * s)),
                       (0.009 * s, 0.006 * s, 0.013 * s), [M["glow"]], 8, 5), knee_spec)
    # 护胫：三片整圈叠压，上片带小腿肚隆起，前脊凸棱，下缘前尖角，最下一片外扩成踝口
    out_s = Vector((0, 1, 0))
    sl = (ankle - knee).length
    plan = ((0.075, 0.42, 0.078, 0.071, 0.008, 0.0, 0.007, 0.034), (0.36, 0.70, 0.071, 0.062, 0.004, 0.0, 0.003, 0.030),
            (0.64, 0.965, 0.063, 0.052, 0.003, 0.014, 0.0, 0.026))
    outers = []
    for k, (v0, v1, r0, r1, f0, f1, bu, dr) in enumerate(plan):
        pt, outer = band3(ctx, f"{ctx.title} greave {label}{k}", knee, ankle, r0 * s, r1 * s, M["plate"], shin_spec,
                          out_s, closed=True, v0=v0, v1=v1, bulge=bu * s, ridge=0.014 * s, flare0=f0 * s,
                          flare1=f1 * s, drop=dr * s, thick=0.0055 * s, nu=20, nv=6, trim_mat=M["silver"],
                          trim_r=0.0034 * s, rims=(1,), rim_n=22)
        outers.append(outer)
        if k < 2:
            ax_, o_, _w = limb_frame(knee, ankle, out_s)
            tip = outer(0.0, 1.0, 0.0)
            d = (-ax_ * 0.85 + o_ * 0.55).normalized()
            ctx.part(crystal2(f"{ctx.title} greave tip {label}{k}", tip - d * 0.006 * s, tip + d * 0.046 * s, 0.0080 * s,
                              [crystal_mat], sides=5, shoulder=0.55, foot=0.8, seed=k * 2.1 + side + 5), shin_spec)
    # 前脊上的浮雕霜纹（沿胫骨前缘一枝长枝晶）；整圈甲片 u=0 / 1 为前方
    fern(ctx, outers[0], shin_spec, M["silver"], f"{ctx.title} greave fern {label}0", 0.0, 0.12, 0.88,
         wu=0.45 * s, wv=0.34 * sl, r=0.0022 * s)
    axis, o, w = limb_frame(knee, ankle, out_s)
    line = [knee.lerp(ankle, lerp(0.12, 0.92, i / 14)) + o * (lerp(0.078, 0.052, i / 14) * s + 0.0165 * s)
            for i in range(15)]
    ctx.part(trim(f"{ctx.title} greave inlay {label}", line, 0.0020 * s, M["inlay"], n=3), shin_spec)
    for k, t in enumerate((0.30, 0.72)):
        g = knee.lerp(ankle, t) + o * (lerp(0.078, 0.052, (t - 0.12) / 0.80) * s + 0.0178 * s)
        ctx.part(ellipsoid(f"{ctx.title} greave gem {label}{k}", g, (0.007 * s, 0.005 * s, 0.009 * s), [M["glow"]],
                           8, 5), shin_spec)
    # 小腿外侧冰晶翼（与大腿翼呼应，滑行时后掠）
    for k, (t, L_, r_) in enumerate(((0.30, 0.085, 0.013), (0.48, 0.060, 0.010))):
        base = knee.lerp(ankle, t) + Vector((side * 0.073 * s, -0.012 * s, 0))
        d = Vector((side * 0.70, -0.55, -0.35)).normalized()
        ctx.part(crystal2(f"{ctx.title} greave wing {label}{k}", base - d * 0.008 * s, base + d * L_ * s, r_ * s,
                          [crystal_mat], sides=5, shoulder=0.6, foot=0.7, seed=k * 2.7 + side + 3), shin_spec)
    return kc


# ===== 臂甲与护手 =====
def arm_armor3(ctx, B, side, label, M, crystal_mat):
    """上臂外层：两片叠压的冰白臂甲罩在深蓝大衣袖上；前臂：两片叠压护臂（腕口外扩成喇叭）、肘部冰晶护肘与背向冰翼。"""
    s = B.s
    a = B.arms[label]
    sl = s
    up = ("rigid", {f"UpperArm.{label}": 1.0})
    fo = ("rigid", {f"Forearm.{label}": 1.0})
    sh, el, wr = a["shoulder"], a["elbow"], a["wrist"]
    ul = (el - sh).length
    out_u = Vector((side, 0, 0.45))
    for k, (v0, v1, r0, r1, dr) in enumerate(((0.30, 0.64, 0.068, 0.064, 0.026), (0.58, 0.90, 0.064, 0.058, 0.022))):
        pt, outer = band3(ctx, f"{ctx.title} rerebrace {label}{k}", sh, el, r0 * sl, r1 * sl, M["plate"], up, out_u,
                          arc=1.45, v0=v0, v1=v1, drop=dr * sl, flare1=0.008 * sl, ridge=0.006 * sl, thick=0.0055 * s,
                          nu=18, nv=5, trim_mat=M["silver"], trim_r=0.0032 * s, rims=(1,), rim_n=16)
        if k == 0:
            fern(ctx, outer, up, M["silver"], f"{ctx.title} rerebrace fern {label}", 0.5, 0.15, 0.82,
                 wu=2 * 1.45 * 0.068 * sl, wv=0.34 * ul, r=0.0020 * s,
                 branches=((0.30, 0.030), (0.55, 0.026), (0.78, 0.020)))
    # 肘：冰晶护肘（朝后外方的一枚大冰晶 + 两枚小的）
    ctx.part(ellipsoid(f"{ctx.title} couter {label}", el + Vector((side * 0.010 * s, -0.016 * s, 0)),
                       (0.040 * s, 0.040 * s, 0.040 * s), [M["plate"]], 14, 8),
             ("rigid", {f"UpperArm.{label}": 0.5, f"Forearm.{label}": 0.5}))
    ring = [el + Vector((side * 0.010 * s, -0.016 * s, 0)) + Vector((math.cos(t) * 0.042 * s, math.sin(t) * 0.042 * s, 0))
            for t in [i / 18 * TAU for i in range(18)]]
    ctx.part(trim(f"{ctx.title} couter ring {label}", ring, 0.0024 * s, M["silver"], closed=True, n=3),
             ("rigid", {f"UpperArm.{label}": 0.5, f"Forearm.{label}": 0.5}))
    fdir = (wr - el).normalized()
    for k, (d, L_, r_) in enumerate(((Vector((side * 0.55, -0.70, 0.45)), 0.115, 0.017),
                                      (Vector((side * 0.95, -0.25, 0.20)), 0.070, 0.011),
                                      (Vector((side * 0.30, -0.45, 0.85)), 0.060, 0.010))):
        d = d.normalized()
        b0 = el + Vector((side * 0.012 * s, -0.020 * s, 0.004 * s)) + d * 0.030 * s
        ctx.part(crystal2(f"{ctx.title} elbow crystal {label}{k}", b0 - d * 0.010 * s, b0 + d * L_ * s, r_ * s,
                          [crystal_mat], sides=5, shoulder=0.6, foot=0.6, seed=k * 1.3 + side), fo)
    # 前臂：两片叠压护臂 + 腕口喇叭 + 冷光嵌线 + 背向冰翼
    a0, a1 = el + fdir * 0.040 * s, wr - fdir * 0.006 * s
    out = Vector((side, -0.35, 0.25))
    fl = (a1 - a0).length
    outer_f = None
    for k, (v0, v1, r0, r1, dr, f1) in enumerate(((0.00, 0.56, 0.054, 0.050, 0.024, 0.006),
                                                   (0.50, 1.00, 0.050, 0.047, 0.020, 0.016))):
        pt, outer = band3(ctx, f"{ctx.title} vambrace {label}{k}", a0, a1, r0 * sl, r1 * sl, M["plate"], fo, out,
                          closed=True, v0=v0, v1=v1, drop=dr * sl, flare1=f1 * sl, ridge=0.005 * sl,
                          thick=0.0052 * s, nu=18, nv=6, trim_mat=M["silver"], trim_r=0.0032 * s, rims=(1,), rim_n=20)
        if k == 0:
            outer_f = outer
    fern(ctx, outer_f, fo, M["silver"], f"{ctx.title} vambrace fern {label}", 0.0, 0.14, 0.86, wu=0.34 * sl,
         wv=0.5 * fl, r=0.0020 * s, branches=((0.28, 0.030), (0.52, 0.026), (0.76, 0.020)))
    axis, o, w = limb_frame(a0, a1, out)
    line = [a0.lerp(a1, t) + o * (lerp(0.054, 0.049, t) * sl + 0.0105 * s) for t in [i / 12 for i in range(13)]]
    ctx.part(trim(f"{ctx.title} vambrace inlay {label}", line, 0.0019 * s, M["inlay"], n=3), fo)
    # 前臂背向冰翼：沿前臂外背侧向肘后掠出一枚细长冰晶，滑行摆臂时拉出剪影
    d = (-fdir * 0.55 + o * 0.85).normalized()
    b0 = a0.lerp(a1, 0.30) + o * 0.058 * s
    ctx.part(crystal2(f"{ctx.title} forearm wing {label}", b0 - d * 0.006 * s, b0 + d * 0.120 * s, 0.013 * s,
                      [crystal_mat], sides=5, shoulder=0.55, foot=0.8, seed=side * 2.0 + 1), fo)


def gauntlet3(ctx, B, M, side, label, h):
    """护手：腕口银环 + 手背弧形甲片（两节）+ 指节脊 + 手背冷光点；h 为 kit.humanoid.hand 的返回值。"""
    s = B.s
    wrist, f, n, sv = h["wrist"], h["f"], h["n"], h["s"]
    sc = 1.20
    hs = ("rigid", {f"Hand.{label}": 1.0})
    ring = [wrist + f * 0.012 * s + (sv * math.cos(t) * 0.040 * s + n * math.sin(t) * 0.032 * s)
            for t in [i / 16 * TAU for i in range(16)]]
    ctx.part(trim(f"{ctx.title} wrist ring {label}", ring, 0.0032 * s, M["silver"], closed=True, n=3), hs)
    for k, (t0, t1, wd) in enumerate(((0.012, 0.050, 0.034), (0.046, 0.090, 0.036))):
        def pt(u, v, t0=t0, t1=t1, wd=wd, k=k):
            x = (2 * u - 1)
            c = wrist + f * lerp(t0, t1, v) * s * sc
            bulge = 0.026 + 0.012 * (1 - x * x) + 0.003 * k
            return c + sv * x * wd * s * sc * (1 - 0.18 * v) - n * bulge * s * sc
        obj = surface(f"{ctx.title} hand plate {label}{k}", pt, 12, 4, [M["plate"]])
        orient(obj, lambda c: wrist + f * 0.05 * s * sc)
        ctx.part(finish(obj, 0.0042 * s, 1, 0), hs)
        edge = [pt(i / 11, 1.0) - n * 0.0042 * s * 1.1 for i in range(12)]
        ctx.part(trim(f"{ctx.title} hand plate rim {label}{k}", edge, 0.0020 * s, M["silver"], n=3), hs)
    c = wrist + f * 0.072 * s * sc - n * 0.044 * s * sc
    ctx.part(ellipsoid(f"{ctx.title} hand gem {label}", c, (0.006 * s, 0.006 * s, 0.006 * s), [M["glow"]], 6, 4), hs)


# ===== 躯干甲 =====
def shell3(ctx, B, name, zt, zb, grow, mat, spec, trim_mat=None, trim_r=0.003, trim_n=40, sides=True, bev=0.0017,
           a0=0.0, a1=TAU, thick=0.008, nu=56, nv=18, shape=None, top_trim=True):
    """贴合躯干的甲壳（改写自 kit.humanoid.shell + _isolde2_kit.shell2）：本体加倒角（板边吃光读出厚度），
    滚边为可控点数的 4 边管；shape(a, z) 返回额外外扩（压出凸棱）。返回 pt(u, v)。"""
    full = abs(a1 - a0 - TAU) < 1e-6
    zt_f = zt if callable(zt) else (lambda a: zt)
    zb_f = zb if callable(zb) else (lambda a: zb)

    def pt(u, v):
        a = a0 + u * (a1 - a0)
        z = lerp(zt_f(a), zb_f(a), v)
        g = grow + (shape(a, z) if shape else 0.0)
        return B.torso_point(a, z, g)
    obj = surface(name, pt, nu, nv, [mat], closed_u=full)
    orient(obj, axis_ref)
    ctx.part(finish3(obj, thick, bev), spec)
    if trim_mat:
        center = lambda p: Vector((0, B.torso_r(p.z)[2], p.z))
        for v in ((0.0, 1.0) if top_trim else (1.0,)):
            pts = [pt(i / (trim_n if full else trim_n - 1), v) for i in range(trim_n)]
            pts = [p + (p - center(p)).normalized() * (thick * 1.05 + trim_r * 0.15) for p in pts]
            ctx.part(trim(f"{name} trim {v}", pts, trim_r, trim_mat, closed=full, n=3), spec)
        if sides and not full:
            for u in (0.0, 1.0):
                pts = [pt(u, j / 12) for j in range(13)]
                pts = [p + (p - center(p)).normalized() * (thick * 1.05 + trim_r * 0.15) for p in pts]
                ctx.part(trim(f"{name} side {u}", pts, trim_r, trim_mat, n=3), spec)
    return pt


def icicle_fringe(ctx, pt, M, spec, name, count=7, u0=0.10, u1=0.90, v=1.0, out_amt=0.55, lens=(0.085, 0.050),
                  r=0.0105, s=1.0, seed=0.0, center=None):
    """甲片下缘垂挂的小冰棱（霜凝在甲沿上）：沿 pt(u, v) 等距分布，中间长、两端短，朝下偏外。"""
    from chars._isolde2_kit import crystal2
    for k in range(count):
        f = k / max(1, count - 1)
        u = lerp(u0, u1, f)
        b = pt(u, v)
        if center is None:
            outward = Vector((b.x, b.y, 0)).normalized()
        else:
            outward = (Vector((b.x, b.y, 0)) - Vector((center.x, center.y, 0))).normalized()
        d = (Vector((0, 0, -1)) + outward * out_amt).normalized()
        mid = 1 - abs(2 * f - 1)
        L = lerp(lens[1], lens[0], mid) * (0.75 + 0.5 * ((k * 0.618 + seed) % 1.0)) * s
        rr = r * s * (0.7 + 0.5 * mid)
        base = b + outward * 0.004 * s
        ctx.part(crystal2(f"{name} {k}", base - d * 0.006 * s, base + d * L, rr, [M["crystal"]], sides=5,
                          shoulder=0.55, foot=0.8, seed=k + seed, twist=k * 0.6), spec)


def torso_plates3(ctx, B, M, spec_ch):
    """胸甲之上再叠一层：双半月胸甲（两道 V 形凸棱 + 下缘冰棱）+ 三道腹甲片。
    返回上层胸甲的 pt 函数，供浮雕霜星定位。"""
    s = B.s
    T = ctx.title

    def chevrons(a, z):
        kz = (z - B.hover) / s
        r = 0.0
        for z0 in (1.505, 1.585):
            r += 0.0075 * s * math.exp(-((kz - (z0 + 0.20 * abs(a) ** 1.1)) / 0.0105) ** 2)
        return r * smoothstep(0.95, 0.80, abs(a))
    up = shell3(ctx, B, f"{T} breastplate", lambda a: B.z(1.668) - 0.050 * s * max(0.0, math.cos(a)) ** 5,
                lambda a: B.z(1.468) - 0.070 * s * max(0.0, math.cos(a)) ** 3, 0.034 * s, M["plate"], spec_ch,
                trim_mat=M["silver"], trim_r=0.0034 * s, trim_n=34, thick=0.010 * s, nu=48, nv=18, a0=-0.98,
                a1=0.98, shape=chevrons)
    icicle_fringe(ctx, up, M, spec_ch, f"{T} breast icicle", count=9, u0=0.12, u1=0.88, v=1.0, lens=(0.095, 0.040),
                  s=s, seed=1.3)
    for k, (zt, zb, g) in enumerate(((1.452, 1.384, 0.034), (1.402, 1.334, 0.031), (1.352, 1.288, 0.028))):
        shell3(ctx, B, f"{T} abdomen lame {k}", B.z(zt),
               lambda a, zb=zb: B.z(zb) - 0.030 * s * max(0.0, math.cos(a)) ** 4, g * s, M["plate"],
               invdist(["Spine", "Chest"]), trim_mat=M["silver"], trim_r=0.0028 * s, trim_n=26, sides=False,
               a0=-0.92, a1=0.92, nu=26, nv=4, thick=0.0055 * s, top_trim=(k == 0))
    return up


# ===== 冰刃铁靴 =====
BOOT_PROF = [(-0.082, (0.036, 0.120)), (-0.062, (0.050, 0.178)), (-0.030, (0.056, 0.204)), (0.020, (0.058, 0.158)),
             (0.075, (0.060, 0.128)), (0.135, (0.056, 0.108)), (0.195, (0.044, 0.094)), (0.250, (0.022, 0.082)),
             (0.272, (0.008, 0.078))]
BOOT_Z0 = 0.066          # 靴底高度（冰刃立柱顶面在 hover + 0.004 = 0.062）


def boot3(ctx, B, M, side, label):
    """铁靴：放样的靴身（后跟高、脚背缓降、尖头）+ 四片叠压脚背甲 + 脚踝喇叭口 + 趾尖冰晶 + 后跟冰刺。
    靴身蒙皮在 Foot / Toe 之间平滑过渡，脚背甲刚性挂 Foot；剖面表 BOOT_PROF 为 (y, (半宽, 顶高))，单位米。"""
    from kit.core import interp, loft
    s = B.s
    L = B.legs[label]
    ankle, ball = L["ankle"], L["ball"]
    x0 = (ankle.x + ball.x) / 2
    zb = BOOT_Z0

    def at(y):
        w, zt = interp(BOOT_PROF, y)
        return w * s, zt * s

    secs = []
    for y, (w, zt) in BOOT_PROF:
        zc, hh = (zt * s + zb) / 2, max(0.006, (zt * s - zb) / 2)
        ring = []
        for k in range(12):
            a = TAU * k / 12
            c, sn = math.cos(a), math.sin(a)
            ring.append(Vector((x0 + w * s * math.copysign(abs(c) ** 0.72, c), y * s,
                                zc + hh * math.copysign(abs(sn) ** 0.72, sn))))
        secs.append(ring)
    body = loft(f"{ctx.title} boot {label}", secs, [M["plate"]], closed_u=True, cap=True)
    ctx.part(body, chain([f"Foot.{label}", f"Toe.{label}"], f"Shin.{label}", 0.03))
    foot_spec = ("rigid", {f"Foot.{label}": 1.0})
    toe_spec = ("rigid", {f"Toe.{label}": 1.0})
    # 脚背四片叠压甲：横向弧片，越靠前越窄，下缘（朝趾尖）中线尖出
    for k, (ya, yb) in enumerate(((-0.044, 0.008), (-0.004, 0.046), (0.036, 0.088), (0.080, 0.138))):
        def pt(u, v, ya=ya, yb=yb):
            a = (u * 2 - 1) * 1.25
            y = lerp(ya, yb, v)
            w, zt = at(y)
            hh = max(0.006, (zt - zb) / 2)
            return Vector((x0 + (w + 0.006 * s) * math.sin(a), y * s + 0.016 * s * v * math.cos(a) ** 3,
                           zt + 0.005 * s - hh * 0.95 * (1 - math.cos(a))))
        obj = surface(f"{ctx.title} instep {label}{k}", pt, 14, 4, [M["plate"]])
        orient(obj, lambda c: Vector((x0, c.y, zb + 0.02 * s)))
        ctx.part(finish3(obj, 0.0050 * s, 0.0017 * s), foot_spec)
        edge = [pt(i / 13, 1.0) + Vector((0, 0.003 * s, 0.004 * s)) for i in range(14)]
        ctx.part(trim(f"{ctx.title} instep rim {label}{k}", edge, 0.0030 * s, M["silver"], n=3), foot_spec)
    # 脚踝喇叭口（整圈、外扩）+ 银沿 + 冷光环
    cen = Vector((x0, -0.030 * s, 0.150 * s))
    for z, r in ((0.000, 0.064), (0.040, 0.070)):
        ring = [cen + Vector((math.sin(a) * r * s, math.cos(a) * r * s * 0.95, z * s))
                for a in [i / 16 * TAU for i in range(16)]]
        ctx.part(trim(f"{ctx.title} ankle cuff {label}{z}", ring, 0.0036 * s, M["silver"], closed=True, n=3),
                 foot_spec)
    glow = [cen + Vector((math.sin(a) * 0.0675 * s, math.cos(a) * 0.0675 * s * 0.95, 0.020 * s))
            for a in [i / 16 * TAU for i in range(16)]]
    ctx.part(trim(f"{ctx.title} ankle glow {label}", glow, 0.0020 * s, M["inlay"], closed=True, n=3), foot_spec)
    # 趾尖冰晶（朝前微上）与后跟冰刺（朝后）、脚踝外侧冰翅
    tip = Vector((x0, 0.262 * s, 0.076 * s))
    ctx.part(crystal2(f"{ctx.title} toe crystal {label}", tip - Vector((0, 0.030 * s, 0)),
                      tip + Vector((0, 0.085 * s, 0.022 * s)), 0.017 * s, [M["crystal"]], sides=5, shoulder=0.55,
                      foot=0.9, seed=side + 4.0), ("rigid", {f"Toe.{label}": 1.0}))
    heel = Vector((x0, -0.078 * s, 0.100 * s))
    ctx.part(crystal2(f"{ctx.title} heel crystal {label}", heel, heel + Vector((0, -0.075 * s, 0.045 * s)), 0.015 * s,
                      [M["crystal"]], sides=5, shoulder=0.55, foot=0.9, seed=side + 6.0), foot_spec)
    for sd in (-1, 1):
        base = Vector((x0 + sd * 0.056 * s, -0.030 * s, 0.176 * s))
        d = Vector((sd * 0.75, -0.55, 0.45)).normalized()
        ctx.part(crystal2(f"{ctx.title} ankle fin {label}{sd}", base - d * 0.006 * s, base + d * 0.075 * s, 0.012 * s,
                          [M["crystal"]], sides=5, shoulder=0.55, foot=0.8, seed=sd * 1.5 + side), foot_spec)


# ===== 滑冰 2.0：重心转移 + 髋肩反向拧转 + 蹬冰腿侧后伸展 + 双臂一前一后 =====
SKATE3 = [
    (0.00, (0.012, 0.100, 0.000, 0.04, 0.00)),    # 前送落冰
    (0.20, (0.016, 0.022, 0.000, 0.05, 0.00)),    # 长滑行（重心压在这只脚上）
    (0.40, (0.052, -0.090, 0.000, 0.22, 0.00)),   # 开始蹬冰
    (0.56, (0.135, -0.215, 0.000, 0.44, 0.05)),   # 侧后蹬出
    (0.68, (0.155, -0.340, 0.115, 0.36, 0.55)),   # 离冰，浮足侧后伸展
    (0.80, (0.115, -0.320, 0.150, 0.22, 0.62)),   # 浮足抬高保持
    (0.91, (0.045, -0.070, 0.075, 0.08, 0.30)),   # 收回
]


def skate3(rig, B, t, pose=None, lean=0.21, sink=0.100, shift=0.060):
    """花样滑冰式长滑步：t∈[0,2π) 左右各一步。
    重心：骨盆横移到滑行脚上方并随蹬冰深蹲；躯干整体前倾约 20°，头部反向补偿保持前视；
    髋与肩反向拧转（骨盆转向蹬冰侧、胸腔反向），蹬冰腿向侧后方伸展并抬起；
    双臂连续一前一后摆动：前手斜前方近水平舒展，后手向后下方拉长，肘腕随之转动，每一帧剪影都不同。"""
    s = B.s
    pose = {} if pose is None else pose
    legs = Legs(rig, B)
    gl = math.cos(t - 1.26)                      # 左脚滑行中段 +1，右脚滑行中段 -1
    push = max(0.0, -math.cos(2 * t - 0.5))       # 蹬冰深蹲：每步一次
    pose["_hover"] = Vector((-shift * s * gl, 0.010 * s * math.sin(2 * t + 0.4),
                             -sink * s - 0.016 * s * push + 0.012 * s * math.cos(2 * t - 0.5)))
    pose["Pelvis"] = R((Z, -0.20 * gl), (Y, -0.075 * gl), (X, -lean - 0.03 * push))
    pose["Spine"] = R((Z, 0.12 * gl), (Y, 0.04 * gl), (X, -0.09))
    pose["Chest"] = R((Z, 0.17 * gl), (Y, 0.05 * gl), (X, -0.05 + 0.014 * math.cos(2 * t)))
    pose["Neck"] = R((X, 0.11), (Z, -0.08 * gl))
    pose["Head"] = R((X, 0.12), (Z, -0.07 * gl))
    for label, ph in (("L", 0.0), ("R", 0.5)):
        side = -1 if label == "L" else 1
        p = (t / TAU + ph) % 1.0
        dx, dy, dz, yaw, pitch = cyc_hermite(SKATE3, p)
        if p < ON_ICE2:
            dz = 0.0
        base = legs.rest[label]["ankle"]
        a = Vector((base.x + side * dx * s, base.y + dy * s, base.z + max(0.0, dz) * s))
        legs.plant(pose, label, a, pitch=pitch, yaw=-side * yaw, knee_out=0.24)
    for label in ("L", "R"):
        side = -1 if label == "L" else 1
        f = 0.5 + 0.5 * math.sin(math.pi / 2 * clamp(gl * side * 1.15, -1, 1))    # 连续摆动，两端略停留
        phi = lerp(math.radians(-54), math.radians(34), f)
        el = lerp(math.radians(-36), math.radians(-6), f) + 0.05 * math.sin(2 * t + side)
        rig.aim(pose, f"UpperArm.{label}", arm_dir(side, phi, el))
        fore = arm_dir(side, phi + math.radians(lerp(-5, 16, f)), el + math.radians(lerp(-5, 20, f)))
        rig.aim(pose, f"Forearm.{label}", fore)
        hand = arm_dir(side, phi + math.radians(lerp(-10, 10, f)), el + math.radians(lerp(-3, 8, f)))
        palm = Vector((0, -0.7, -0.7)).lerp(Vector((0, 0.15, -1.0)), f)
        rig.aim(pose, f"Hand.{label}", hand, up=tuple(palm), rest_up=B.hands[label]["n"])
    return pose
