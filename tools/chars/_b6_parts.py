"""Boss 6 · 剧毒三位体 私有部件：蝰蛇机械头、蒙皮长颈（叠甲 / 金箍 / 腹侧毒管 / 分层颈甲）、
短粗机械腿、盘尾、毒液储罐与管路。只被 tools/chars/boss_6.py 引用。

头部在局部单位坐标（原点为颈端关节，+Y 吻部、+Z 头顶、+X 右侧，长约 1.2）建模，
再按 frame_matrix(颈端, 头朝向, 头顶向, 头部缩放) 整体摆到世界。
"""

import math

from mathutils import Matrix, Vector

from kit.core import (TAU, catmull, chain, clamp, ellipsoid, finish, interp, lerp, orient, plate, rigid,
                      smoothstep, spike, surface, transform, tube)

from chars import _b6fx_spray as FX
from chars._b6_kit import (Spine, blob, circle_y, frame_matrix, lathe_y, orth, rot, sgnpow, spine_shell,
                           spine_tube, surf_normal)

SPRAY_K = 0.02          # 毒雾在静止姿态下的缩小倍率（动作里按 1/SPRAY_K 放大）


def trim(name, points, radius, mat, closed=False, per=1):
    """滚边 / 嵌线细管：按半径取 4 或 5 边截面（这些材质不参与游戏版减面，需要自己控制面数）。"""
    return tube(name, points, [radius] * len(points), [mat], n=4 if radius < 0.0095 else 5, closed=closed, per=per)


def gem(name, center, size, mat, stretch=(1.0, 0.6, 1.4)):
    """低面数发光宝石 / 液滴（8×6 段）。"""
    return ellipsoid(name, center, (size * stretch[0], size * stretch[1], size * stretch[2]), [mat], 8, 6)


# ===== 通用小件 =====
def blade_outline(L, w, back=0.35, n=10, curve=0.0):
    """刃羽轮廓：x 沿长度 0→L，y 为宽；前缘弧、后缘直，尖端收尖；curve 使整体弯成弧。"""
    top, low = [], []
    for i in range(1, n):
        t = i / n
        c = curve * L * math.sin(math.pi * t) * 0.5
        wt = w * min(1.0, (t / 0.15) ** 0.6) * (1 - smoothstep(0.5, 1.0, t)) ** 0.8
        top.append((t * L, c + wt * (1 - back)))
        low.append((t * L, c - wt * back))
    return [(0.0, 0.0)] + top + [(L, 0.0)] + list(reversed(low))


def fin(name, base, d, n_hint, L, w, mat, thick=0.02, back=0.35, curve=0.1, bulge=0.02):
    """刃形甲鳍：从 base 沿 d 伸出，板面法向约为 n_hint。返回 (对象, 轮廓上缘点列函数)。"""
    d = Vector(d).normalized()
    n = orth(n_hint, d)
    ya = n.cross(d).normalized()
    outline = blade_outline(L, w, back, 10, curve)
    bl = lambda x, y: bulge * math.sin(math.pi * clamp(x / L))   # noqa: E731
    obj = plate(name, outline, thick, [mat], origin=base, xaxis=d, yaxis=ya, bulge=bl, bev=thick * 0.25, bev_seg=1)

    def edge(lift=0.0, lo=0.08, hi=0.92, k=12, which=1):
        pts = []
        for i in range(k + 1):
            x = lerp(lo, hi, i / k) * L
            t = x / L
            c = curve * L * math.sin(math.pi * t) * 0.5
            wt = w * min(1.0, (t / 0.15) ** 0.6) * (1 - smoothstep(0.5, 1.0, t)) ** 0.8
            y = c + (wt * (1 - back) + lift if which > 0 else -wt * back - lift)
            pts.append(Vector(base) + d * x + ya * y + n * bl(x, y))
        return pts

    def mid(lift, lo=0.12, hi=0.75, k=10):
        pts = []
        for i in range(k + 1):
            x = lerp(lo, hi, i / k) * L
            t = x / L
            c = curve * L * math.sin(math.pi * t) * 0.5
            y = c + w * 0.18 * (1 - t)
            pts.append(Vector(base) + d * x + ya * y + n * (bl(x, y) + thick * 0.5 + lift))
        return pts
    return obj, edge, mid


# ===== 蝰蛇机械头 =====
Y_B, Y_F = -0.20, 1.02
SKULL_W = [(-0.20, 0.16), (0.02, 0.26), (0.24, 0.31), (0.52, 0.25), (0.78, 0.18), (0.92, 0.13), (1.02, 0.09)]
SKULL_HT = [(-0.20, 0.15), (0.08, 0.21), (0.36, 0.20), (0.70, 0.14), (1.02, 0.085)]
SKULL_HB = [(-0.20, 0.10), (0.15, 0.052), (1.02, 0.042)]
SKULL_Z = [(-0.20, 0.07), (0.30, 0.018), (1.02, -0.004)]
J_B, J_F = 0.02, 0.98
JAW_W = [(0.02, 0.20), (0.30, 0.205), (0.60, 0.155), (0.85, 0.10), (0.98, 0.06)]
JAW_HB = [(0.02, 0.105), (0.35, 0.115), (0.70, 0.09), (0.98, 0.045)]
JAW_ZC = -0.049
HINGE = Vector((0, 0.06, -0.05))
DRIP_H, DRIP_T = Vector((0, 0.805, -0.245)), Vector((0, 0.805, -0.42))
SPRAY_H, SPRAY_D = Vector((0, 0.42, -0.04)), Vector((0, 1, -0.10)).normalized()


def _ends(y, y0, y1, k):
    s = clamp((y - (y0 + y1) / 2) / ((y1 - y0) / 2), -1, 1)
    return math.sin(math.acos(s)) ** k


def skull_at(a, y):
    rho = _ends(y, Y_B, Y_F, 0.42)
    w = interp(SKULL_W, y) * rho
    ht = interp(SKULL_HT, y) * rho
    hb = interp(SKULL_HB, y) * rho
    zc = interp(SKULL_Z, y)
    ca, sa = math.cos(a), math.sin(a)
    x = w * sgnpow(sa, 2 / 2.4)
    z = zc + (ht * sgnpow(ca, 2 / 2.2) if ca >= 0 else hb * sgnpow(ca, 2 / 3.4))
    brow = 0.030 * math.exp(-((y - 0.50) / 0.11) ** 2) * math.exp(-((abs(x) - 0.16) / 0.06) ** 2) * smoothstep(0.1, 0.5, ca)
    ridge = 0.014 * math.exp(-(x / 0.035) ** 2) * smoothstep(-0.05, 0.35, y) * smoothstep(0.5, 0.9, ca)
    return Vector((x, y, z + brow + ridge))


def skull_off(a, y, extra):
    ref = Vector((0, y, interp(SKULL_Z, y)))
    return skull_at(a, y) + surf_normal(skull_at, a, y, ref) * extra


def jaw_at(a, y):
    rho = _ends(y, J_B, J_F, 0.40)
    w = interp(JAW_W, y) * rho
    hb = interp(JAW_HB, y) * rho
    ca, sa = math.cos(a), math.sin(a)
    x = w * sgnpow(sa, 2 / 2.4)
    z = JAW_ZC + (0.013 * rho * sgnpow(ca, 0.8) if ca >= 0 else hb * sgnpow(ca, 2 / 2.4))
    return Vector((x, y, z))


def jaw_off(a, y, extra):
    return jaw_at(a, y) + surf_normal(jaw_at, a, y, Vector((0, y, JAW_ZC - 0.04))) * extra


def _yv(v, y0, y1):
    return (y0 + y1) / 2 + (y1 - y0) / 2 * math.cos(math.pi * v)


def build_head(ctx, M, S, H):
    """H: {O 颈端, fwd 头朝向, up 头顶向, hs 缩放, king 是否主首}。返回世界坐标骨骼关键点。"""
    t = f"{ctx.title} head {S}"
    king = H["king"]
    mw = frame_matrix(H["O"], H["fwd"], H["up"], H["hs"])
    hsp, jsp = rigid(f"Head{S}"), rigid(f"Jaw{S}")

    def add(obj, spec):
        transform(obj, mw)
        return ctx.part(obj, spec)

    # 头骨与下颌（雕花漆甲）
    skull = surface(f"{t} skull", lambda u, v: skull_at(u * TAU, _yv(v, Y_B, Y_F)), 60, 44, [M["armor"]],
                    closed_u=True, uvfn=lambda u, v: (u * 2, v * 1.6))
    add(orient(skull, lambda c: Vector((0, c.y, 0.02))), hsp)
    jaw = surface(f"{t} jaw", lambda u, v: jaw_at(u * TAU, _yv(v, J_B, J_F)), 48, 30, [M["armor"]],
                  closed_u=True, uvfn=lambda u, v: (u * 2, v * 1.2))
    add(orient(jaw, lambda c: Vector((0, c.y, JAW_ZC - 0.03))), jsp)
    # 口腔：上颚 / 舌床发光毒膜 + 喉部毒囊（张口时露出）
    pal = [(interp(SKULL_W, y) * _ends(y, Y_B, Y_F, 0.42) * 0.74, y) for y in [0.12 + i * 0.06 for i in range(13)]]
    add(plate(f"{t} palate", [(x, y) for x, y in pal] + [(-x, y) for x, y in reversed(pal)], 0.004,
              [M["venom"]], origin=(0, 0, -0.036), xaxis=(1, 0, 0), yaxis=(0, 1, 0)), hsp)
    ton = [(interp(JAW_W, y) * _ends(y, J_B, J_F, 0.40) * 0.72, y) for y in [0.10 + i * 0.06 for i in range(13)]]
    add(plate(f"{t} tongue bed", [(x, y) for x, y in ton] + [(-x, y) for x, y in reversed(ton)], 0.004,
              [M["venom"]], origin=(0, 0, -0.033), xaxis=(1, 0, 0), yaxis=(0, 1, 0)), jsp)
    add(blob(f"{t} gullet", (0, 0.17, -0.036), (0.11, 0.07, 0.030), [M["venom"]], 16, 10), hsp)
    # 眼：狭长发光眼 + 金眼眶
    for sd in (-1, 1):
        ae, ye = sd * 1.10, 0.56
        add(gem(f"{t} eye {sd}", skull_off(ae, ye, 0.006), 0.030, M["glow"], (0.85, 2.5, 1.0)), hsp)
        ring = [skull_off(sd * (1.10 + 0.19 * math.cos(k / 14 * TAU)), ye + 0.10 * math.sin(k / 14 * TAU), 0.010)
                for k in range(14)]
        add(trim(f"{t} eye rim {sd}", ring, 0.008, M["trim"], closed=True), hsp)
        # 金眉甲：压在眼上方，向后收成尖
        b0 = skull_off(sd * 0.92, 0.70, 0.004)
        d = (skull_off(sd * 0.95, 0.20, 0.03) - b0).normalized()
        obj, edge, _ = fin(f"{t} brow {sd}", b0, d, Vector((sd * 0.5, 0, 1)), 0.55, 0.075, M["gold"],
                           thick=0.018, back=0.55, curve=0.05, bulge=0.012)
        add(obj, hsp)
        # 颊部毒腺 + 三道发光排毒缝
        gc = Vector((sd * 0.255, 0.26, -0.012))
        add(blob(f"{t} gland {sd}", gc, (0.075, 0.15, 0.085), [M["armor"]], 18, 12), hsp)
        for k in range(3):
            y = 0.19 + k * 0.07
            add(tube(f"{t} gland slit {sd}{k}", [gc + Vector((sd * 0.068, y - 0.26, -0.045)),
                                                 gc + Vector((sd * 0.079, y - 0.26 + 0.01, 0.0)),
                                                 gc + Vector((sd * 0.068, y - 0.26 + 0.02, 0.045))],
                     [0.008, 0.009, 0.008], [M["inlay"]], n=4, per=2), hsp)
        # 鼻孔
        add(gem(f"{t} nostril {sd}", skull_off(sd * 0.55, 0.955, 0.002), 0.012, M["glow"], (1, 1.4, 0.8)), hsp)
        # 唇线金边 + 头侧嵌线
        lip = [skull_off(sd * math.pi / 2, y, 0.004) for y in [0.06 + i * 0.075 for i in range(13)]]
        add(trim(f"{t} lip {sd}", lip, 0.008, M["trim"]), hsp)
        inl = [skull_off(sd * 0.78, y, 0.003) for y in [0.46 - i * 0.07 for i in range(8)]]
        add(trim(f"{t} inlay {sd}", inl, 0.0055, M["inlay"]), hsp)
        # 下颌：金唇线、侧嵌线
        jl = [jaw_off(sd * math.pi / 2, y, 0.003) for y in [0.05 + i * 0.078 for i in range(12)]]
        add(trim(f"{t} jaw lip {sd}", jl, 0.0072, M["trim"]), jsp)
        ji = [jaw_off(sd * (math.pi / 2 + 0.45), y, 0.003) for y in [0.12 + i * 0.10 for i in range(8)]]
        add(trim(f"{t} jaw inlay {sd}", ji, 0.005, M["inlay"]), jsp)
        # 牙：上排小齿（挂在下颌外侧）、下排小齿、主毒牙 + 牙尖毒滴
        for k in range(5):
            y = 0.30 + k * 0.10
            w = interp(SKULL_W, y) * _ends(y, Y_B, Y_F, 0.42) - 0.035
            b = Vector((sd * w, y, -0.028))
            add(spike(f"{t} tooth {sd}{k}", b, b + Vector((0, 0.012, -0.052)), 0.012, [M["fang"]], sides=5), hsp)
        for k in range(6):
            y = 0.24 + k * 0.10
            w = interp(JAW_W, y) * _ends(y, J_B, J_F, 0.40) - 0.03
            b = Vector((sd * w, y, -0.040))
            add(spike(f"{t} low tooth {sd}{k}", b, b + Vector((0, 0.010, 0.046)), 0.011, [M["fang"]], sides=5), jsp)
        fp = [Vector((sd * 0.135, 0.79, -0.02)), Vector((sd * 0.142, 0.828, -0.10)),
              Vector((sd * 0.144, 0.830, -0.18)), Vector((sd * 0.139, 0.805, -0.245))]
        add(tube(f"{t} fang {sd}", fp, [0.025, 0.020, 0.013, 0.0], [M["fang"]], n=8, per=4), hsp)
        tip = fp[-1]
        add(gem(f"{t} fang drop {sd}", tip + Vector((0, 0, -0.006)), 0.016, M["glow"], (1, 1, 1.3)), hsp)
        add(ellipsoid(f"{t} drip {sd}", tip + Vector((0, 0, -0.050)), (0.013, 0.013, 0.027), [M["glow"]], 10, 8),
            rigid(f"Drip{S}"))
    # 下颌金护颏
    chin = surface(f"{t} chin", lambda u, v: jaw_off(math.pi + lerp(-0.75, 0.75, u), lerp(0.52, 0.95, v), 0.006),
                   14, 8, [M["gold"]])
    add(finish(orient(chin, lambda c: Vector((0, c.y, JAW_ZC))), 0.010, 1, 0), jsp)
    # 吻部金护板 + 头骨后缘金边
    snout = surface(f"{t} snout guard", lambda u, v: skull_off(lerp(-0.62, 0.62, u), lerp(0.70, 1.0, v), 0.008),
                    14, 8, [M["gold"]])
    add(finish(orient(snout, lambda c: Vector((0, c.y, 0))), 0.012, 1, 0), hsp)
    rim = [skull_off(a, 0.02, 0.005) for a in [lerp(-2.2, 2.2, i / 16) for i in range(17)]]
    add(trim(f"{t} rim", rim, 0.009, M["trim"]), hsp)
    # 头冠：中脊锯齿冠 + 两侧三层兜帽鳍（主首更大，另加一对金角）
    ck = 1.3 if king else 1.0
    tops = []
    outline = [(0.0, 0.12)]
    for k in range(5):
        h = 0.20 + (0.05 + 0.045 * k) * ck
        outline += [(0.04 + 0.18 * k, h - 0.05 * ck), (0.13 + 0.18 * k, h)]
        tops += [(0.04 + 0.18 * k, h - 0.05 * ck), (0.13 + 0.18 * k, h)]
    outline += [(0.96, 0.20 + 0.28 * ck), (0.92, 0.34), (0.60, 0.15), (0.30, 0.10)]
    tops += [(0.96, 0.20 + 0.28 * ck)]
    crest = plate(f"{t} crest", outline, 0.024, [M["armor"]], origin=(0, 0.52, 0), xaxis=(0, -1, 0),
                  yaxis=(0, 0, 1), bev=0.005, bev_seg=1)
    add(crest, hsp)
    for sd in (-1, 1):
        add(trim(f"{t} crest edge {sd}", [Vector((sd * 0.013, 0.52 - x, z + 0.004)) for x, z in tops], 0.006,
                 M["trim"], per=1), hsp)
    add(trim(f"{t} crest inlay", [Vector((0, 0.52 - x, 0.16 + 0.16 * x * ck * 0.7)) for x in
                                  [0.10 + i * 0.10 for i in range(8)]], 0.0075, M["inlay"]), hsp)
    for sd in (-1, 1):
        for k in range(3):
            base = skull_off(sd * (1.30 + 0.12 * k), 0.14 - 0.05 * k, -0.02)
            d = Vector((sd * (0.90 - 0.28 * k), -1.0, -0.10 + 0.42 * k))
            L = (0.46 + 0.07 * k) * ck
            mat = M["gold"] if k == 1 else M["armor"]
            obj, edge, mid = fin(f"{t} hood {sd}{k}", base, d, Vector((sd * 0.55, 0.15, 0.85)), L, 0.13 * ck, mat,
                                 thick=0.022, back=0.30, curve=0.14, bulge=0.03)
            add(obj, hsp)
            add(trim(f"{t} hood edge {sd}{k}", edge(0.004, k=8), 0.0068, M["trim"]), hsp)
            if k != 1:
                add(trim(f"{t} hood inlay {sd}{k}", mid(0.002, k=6), 0.005, M["inlay"]), hsp)
        if king:
            b = skull_off(sd * 0.60, 0.34, -0.02)
            add(spike(f"{t} horn {sd}", b, b + Vector((sd * 0.20, -0.62, 0.40)), 0.050, [M["gold"]], sides=8,
                      bend=0.10, up=(0, 0.3, 1)), hsp)
    # 毒雾（静止时缩小藏在口腔里，动作中由 Spray 骨放大）
    build_spray(ctx, M, S, mw, 4.2 / H["hs"])
    return {"hinge": mw @ HINGE, "jaw_tail": mw @ (HINGE + Vector((0, 0.62, -0.04))),
            "drip": (mw @ DRIP_H, mw @ DRIP_T), "spray": (mw @ SPRAY_H, mw @ (SPRAY_H + SPRAY_D * 0.5))}


def build_spray(ctx, M, S, mw, L):
    """半透明毒雾羽流 + 飞溅毒滴 + 喷口光晕（见 _b6fx_spray）：建在 Spray 骨局部系里并整体缩小 SPRAY_K，
    动作里由 Spray 骨缩放放大到满伸（骨名与缩放驱动不变）。"""
    fr = frame_matrix(SPRAY_H, SPRAY_D, (0, 0, 1)) @ Matrix.Scale(SPRAY_K, 4)
    plume = FX.venom_plume(f"{ctx.title} venom plume {S}", L, M["spray"], seed="LCR".index(S) * 2.3 + 0.4)
    transform(plume, mw @ fr)
    ctx.part(plume, rigid(f"Spray{S}"))


# ===== 长颈 =====
def neck_spine(N):
    hs = N["hs"]
    pts = list(N["joints"]) + [N["joints"][-1] + N["hd"] * 0.16 * hs]
    n = len(pts)
    r0, r1 = N["r"]
    radii = [lerp(r0, r1, (i / (n - 2)) ** 0.8) if i < n - 1 else r1 * 0.96 for i in range(n)]
    return Spine(pts, radii, N["up0"], per=6)


def joint_ts(sp, joints):
    out = []
    for j in joints:
        i = min(range(len(sp.P)), key=lambda k: (sp.P[k] - j).length_squared)
        out.append(sp.acc[i] / sp.L)
    return out


def build_neck(ctx, M, S, N):
    t = f"{ctx.title} neck {S}"
    sp = neck_spine(N)
    ts = joint_ts(sp, N["joints"])
    bones = N["bones"]
    skin = chain(bones + [f"Head{S}"], "Chest", 0.10)
    ctx.part(spine_tube(f"{t} skin", sp, [M["scale"]], n=28, t0=-0.04, t1=1.0, tile=0.8), skin)
    # 腹侧发光毒管（颈根一直通到下颌后方）
    cond = [sp.pt(lerp(-0.02, ts[-1] + 0.03, i / 26), math.pi, 0.018) for i in range(27)]
    ctx.part(tube(f"{t} conduit", cond, [0.023] * 27, [M["inlay"]], n=6, per=1), skin)
    A = 1.28
    for j, name in enumerate(bones):
        ta, tb = ts[j], ts[j + 1]
        dt = tb - ta
        for k in range(2):
            v0 = ta + dt * (0.5 * k - 0.12)
            v1 = ta + dt * (0.5 * k + 0.52)
            off0, off1 = 0.058, 0.020
            sh = spine_shell(f"{t} lame {j}{k}", sp, v0, v1, -A, A, off0, off1, [M["armor"]], nu=12, nv=5,
                             arch=0.012)
            ctx.part(finish(sh, 0.022, -1, 0), rigid(name))
            edge = [sp.pt(v0, lerp(-A, A, i / 8), off0 + 0.012 * math.sin(math.pi * i / 8) + 0.004)
                    for i in range(9)]
            ctx.part(trim(f"{t} lame edge {j}{k}", edge, 0.009, M["trim"]), rigid(name))
            if k == 0:
                ctx.part(gem(f"{t} node {j}", sp.pt(v0 + dt * 0.10, 0.0, off0 + 0.004), 0.024, M["glow"],
                             (1, 1, 1)), rigid(name))
        # 腹侧金箍（关节收口，跨过毒管）
        tj = tb if j < len(bones) - 1 else tb - 0.01
        nxt = bones[j + 1] if j < len(bones) - 1 else f"Head{S}"
        band = [sp.pt(tj, a, 0.028 + 0.040 * math.exp(-((a - math.pi) / 0.22) ** 2))
                for a in [lerp(A - 0.05, TAU - A + 0.05, i / 10) for i in range(11)]]
        ctx.part(trim(f"{t} band {j}", band, 0.013, M["trim"]), rigid((name, 0.5), (nxt, 0.5)))
    # 颈根分层颈甲（三层扇贝边锥环，底层固定在躯干上）
    c0, T0 = N["joints"][0], N["t0"]
    D0 = orth(N["up0"], T0)
    B0 = T0.cross(D0)
    r0 = N["r"][0]
    layers = [(-0.34, -0.04, 1.50, 1.38, rigid("Chest")),
              (-0.16, 0.12, 1.38, 1.26, rigid(("Chest", 0.5), (bones[0], 0.5))),
              (0.02, 0.26, 1.26, 1.14, rigid(bones[0]))]
    for k, (zb, zt, rb, rt, spec) in enumerate(layers):
        def cp(u, v, zb=zb, zt=zt, rb=rb, rt=rt, extra=0.0):
            a = u * TAU
            sc = 0.07 * max(0.0, math.cos(6 * a)) ** 3
            z = lerp(zt, zb, v) - sc * v
            r = lerp(rt, rb, v) * r0 * (1 + 0.05 * v * v) + extra
            return c0 + T0 * z + (D0 * math.cos(a) + B0 * math.sin(a)) * r
        col = surface(f"{t} collar {k}", cp, 48, 5, [M["armor"]], closed_u=True, uvfn=lambda u, v: (u * 3, v * 0.5))
        orient(col, lambda c: c0 + T0 * (c - c0).dot(T0))
        ctx.part(finish(col, 0.030, -1, 0), spec)
        ctx.part(trim(f"{t} collar rim {k}", [cp(i / 36, 1.0, extra=0.004) for i in range(36)], 0.012, M["trim"],
                      closed=True), spec)
        if k == 1:
            ctx.part(trim(f"{t} collar inlay", [cp(i / 36, 0.45, extra=0.006) for i in range(36)], 0.007,
                          M["inlay"], closed=True), spec)
    return sp


# ===== 短粗机械腿 =====
def build_leg(ctx, M, label, L):
    t = f"{ctx.title} leg {label}"
    H, K, A, ball = L["hip"], L["knee"], L["ankle"], L["ball"]
    side = L["side"]
    th, sh, ft = f"Thigh.{label}", f"Shin.{label}", f"Foot.{label}"
    body = L["body"]
    d1 = (K - H).normalized()
    d2 = (A - K).normalized()
    skin = chain([th, sh, ft], body, 0.12)
    sp1 = Spine([H - d1 * 0.24, H.lerp(K, 0.5), K + d1 * 0.02], [0.35, 0.33, 0.29], (0, 0, 1), per=4)
    ctx.part(spine_tube(f"{t} thigh", sp1, [M["armor"]], n=22, tile=0.6), skin)
    sp2 = Spine([K - d2 * 0.02, K.lerp(A, 0.5), A + d2 * 0.04], [0.28, 0.25, 0.22], (side, 0, 0), per=4)
    ctx.part(spine_tube(f"{t} shin", sp2, [M["armor"]], n=22, tile=0.6), skin)
    # 大腿金箍 + 膝甲球 + 外侧膝刺
    for tt in (0.35, 0.80):
        ctx.part(trim(f"{t} thigh ring {tt}", [sp1.pt(tt, a, 0.012) for a in [i / 18 * TAU for i in range(18)]],
                      0.016, M["trim"], closed=True), skin)
    ctx.part(blob(f"{t} knee", K, (0.29, 0.29, 0.29), [M["armor"]], 20, 12, tile=0.5),
             rigid((th, 0.5), (sh, 0.5)))
    out = Vector((side, 0.1, 0.55)).normalized()
    ctx.part(blob(f"{t} knee cap", K + out * 0.20, (0.19, 0.19, 0.19), [M["gold"]], 16, 10), rigid(th))
    ctx.part(spike(f"{t} knee spike", K + out * 0.32, K + out * 0.70 + Vector((0, -0.12, 0.14)), 0.085,
                   [M["gold"]], sides=8, bend=0.05), rigid(th))
    # 胫甲（前外侧弧板）+ 上下金箍
    ac = -side * math.pi / 4
    gr = spine_shell(f"{t} greave", sp2, 0.10, 0.86, ac - 1.25, ac + 1.25, 0.045, 0.030, [M["armor"]], 12, 8,
                     arch=0.02)
    ctx.part(finish(gr, 0.022, -1, 0), rigid(sh))
    ctx.part(trim(f"{t} greave edge", [sp2.pt(0.10, lerp(ac - 1.25, ac + 1.25, i / 10),
                                                0.049 + 0.02 * math.sin(math.pi * i / 10)) for i in range(11)],
                  0.012, M["trim"]), rigid(sh))
    ctx.part(trim(f"{t} greave inlay", [sp2.pt(lerp(0.2, 0.8, i / 6), ac, 0.075) for i in range(7)], 0.009,
                  M["inlay"]), rigid(sh))
    for tt in (0.08, 0.94):
        ctx.part(trim(f"{t} shin ring {tt}", [sp2.pt(tt, a, 0.014) for a in [i / 18 * TAU for i in range(18)]],
                      0.016, M["trim"], closed=True), rigid(sh))
    # 足：踝球、宽足垫、三趾象牙爪、后跟距
    fd = Vector((ball.x - A.x, ball.y - A.y, 0)).normalized()
    lat = fd.cross(Vector((0, 0, 1)))
    fr = Matrix((lat, fd, Vector((0, 0, 1)))).transposed()
    ctx.part(blob(f"{t} ankle", A, (0.22, 0.22, 0.18), [M["armor"]], 18, 10, tile=0.5), rigid(ft))
    ctx.part(trim(f"{t} ankle ring", [A + (lat * math.cos(a) + fd * math.sin(a)) * 0.23 + Vector((0, 0, 0.02))
                                      for a in [i / 18 * TAU for i in range(18)]], 0.017, M["trim"], closed=True),
             rigid(ft))
    pc = Vector((A.x, A.y, 0.0)) + fd * 0.22 + Vector((0, 0, 0.115))
    ctx.part(blob(f"{t} pad", pc, (0.31, 0.33, 0.115), [M["armor"]], 22, 12, power=2.6, frame=fr, tile=0.5),
             rigid(ft))
    for k, yaw in enumerate((-0.50, 0.0, 0.50)):
        dd = rot(fd, (0, 0, 1), yaw)
        a0 = pc + dd * 0.18
        a1 = pc + dd * 0.48 + Vector((0, 0, -0.03))
        ctx.part(blob(f"{t} toe {k}", a0.lerp(a1, 0.5), (0.095, 0.18, 0.08), [M["armor"]], 14, 8, power=2.2,
                      frame=Matrix((dd.cross(Vector((0, 0, 1))), dd, Vector((0, 0, 1)))).transposed(), tile=0.4),
                 rigid(ft))
        ctx.part(trim(f"{t} toe ring {k}", [a1 - dd * 0.05 + (dd.cross(Vector((0, 0, 1))) * math.cos(a) +
                                                               Vector((0, 0, 1)) * math.sin(a)) * 0.082
                                            for a in [i / 10 * TAU for i in range(10)]], 0.011, M["trim"], closed=True),
                 rigid(ft))
        ctx.part(spike(f"{t} claw {k}", a1, a1 + dd * 0.22 + Vector((0, 0, -0.06)), 0.06, [M["fang"]], sides=6,
                       bend=0.035), rigid(ft))
    ctx.part(spike(f"{t} spur", pc - fd * 0.24 + Vector((0, 0, 0.02)), pc - fd * 0.46 + Vector((0, 0, -0.04)),
                   0.055, [M["fang"]], sides=6, bend=0.02), rigid(ft))


# ===== 盘尾 =====
def build_tail(ctx, M, pts, radii):
    t = f"{ctx.title} tail"
    ext = pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.10
    sp = Spine(list(pts) + [ext], list(radii) + [radii[-1] * 0.7], (0, 0, 1), per=6)
    bones = [f"Tail{j}" for j in range(1, len(pts))]
    ts = joint_ts(sp, pts)
    skin = chain(bones, "Pelvis", 0.15)
    ctx.part(spine_tube(f"{t} skin", sp, [M["scale"]], n=26, t0=-0.05, t1=1.0, tile=0.8), skin)
    A = 1.30
    for j, name in enumerate(bones):
        ta, tb = ts[j], ts[j + 1]
        dt = tb - ta
        v0, v1 = ta - dt * 0.02, tb + dt * 0.10
        sh = spine_shell(f"{t} lame {j}", sp, v0, v1, -A, A, 0.022, 0.060, [M["armor"]], 14, 7, arch=0.015)
        ctx.part(finish(sh, 0.024, -1, 0), rigid(name))
        ctx.part(trim(f"{t} lame edge {j}", [sp.pt(v1, lerp(-A, A, i / 10), 0.064 + 0.015 * math.sin(math.pi * i / 10))
                                            for i in range(11)], 0.012, M["trim"]), rigid(name))
        ctx.part(trim(f"{t} lame inlay {j}", [sp.pt(lerp(v0 + dt * 0.15, v1 - dt * 0.15, i / 5), 0.0, 0.058)
                                             for i in range(6)], 0.008, M["inlay"]), rigid(name))
        if j < len(bones) - 1:
            c, T, D, Bn, r = sp.frame(lerp(ta, tb, 0.55))
            base = c + D * (r + 0.03)
            h = 0.34 * (1 - 0.13 * j)
            ctx.part(spike(f"{t} spike {j}", base, base + D * h + T * h * 0.55, 0.07 * (1 - 0.1 * j), [M["gold"]],
                           sides=6, bend=0.03, up=T), rigid(name))
        band = [sp.pt(tb, a, 0.020) for a in [lerp(A - 0.1, TAU - A + 0.1, i / 12) for i in range(13)]]
        nxt = bones[j + 1] if j < len(bones) - 1 else name
        ctx.part(trim(f"{t} band {j}", band, 0.013, M["trim"]), rigid((name, 0.5), (nxt, 0.5)))
    # 尾刺：金色弯刃 + 毒囊 + 刃尖毒滴
    c, T, D, Bn, r = sp.frame(1.0)
    end = bones[-1]
    ctx.part(blob(f"{t} venom sac", c - T * 0.04, (0.10, 0.10, 0.12), [M["venom"]], 16, 10,
                  frame=Matrix((Bn, T, D)).transposed()), rigid(end))
    obj, edge, _ = fin(f"{t} stinger", c - T * 0.02, T + D * 0.35, Bn, 0.82, 0.24, M["gold"], thick=0.04,
                       back=0.25, curve=0.25, bulge=0.0)
    ctx.part(obj, rigid(end))
    ctx.part(trim(f"{t} stinger edge", edge(0.004, k=8), 0.009, M["inlay"]), rigid(end))
    tip = c - T * 0.02 + (T + D * 0.35).normalized() * 0.82
    ctx.part(gem(f"{t} stinger drop", tip + Vector((0, 0, -0.02)), 0.022, M["glow"], (1, 1, 1.3)), rigid(end))
    return sp


# ===== 毒液储罐 =====
def tank_matrix(T):
    return frame_matrix(T["base"], T["axis"], (0, -1, 0))


def build_tank(ctx, M, k, T):
    t = f"{ctx.title} tank {k}"
    r, h = T["r"], T["h"]
    mw = tank_matrix(T)
    body = rigid("Chest")

    def add(obj, spec=body):
        transform(obj, mw)
        return ctx.part(obj, spec)
    add(lathe_y(f"{t} liquid", [(0.002, 0.02), (0.93 * r, 0.03), (0.93 * r, h - 0.03), (0.002, h - 0.02)],
                [M["venom"]], 24, uv=lambda u, v: (u * 2, v * h / (math.pi * r))))
    add(lathe_y(f"{t} surge", [(0.002, 0.05), (0.87 * r, 0.06), (0.87 * r, h - 0.06), (0.002, h - 0.05)],
                [M["surge"]], 18), rigid(f"Surge{k}"))
    add(lathe_y(f"{t} base", [(1.16 * r, -0.16), (1.24 * r, -0.07), (1.22 * r, 0.05), (1.10 * r, 0.12),
                              (0.94 * r, 0.13)], [M["armor"]], 40, uv=lambda u, v: (u * 3, v * 0.5)))
    add(lathe_y(f"{t} cap", [(0.94 * r, h - 0.13), (1.12 * r, h - 0.12), (1.20 * r, h - 0.04), (1.13 * r, h + 0.06),
                             (0.84 * r, h + 0.17), (0.45 * r, h + 0.25), (0.16 * r, h + 0.28), (0.002, h + 0.28)],
                [M["armor"]], 40, uv=lambda u, v: (u * 3, v * 0.6)))
    for y, rr in ((-0.07, 1.25 * r), (h - 0.04, 1.21 * r), (h + 0.06, 1.14 * r)):
        add(trim(f"{t} rim {y:.2f}", circle_y(rr, y, 24), 0.013 * (r / 0.3) ** 0.5, M["trim"], closed=True))
    for y in (h / 3, 2 * h / 3):
        add(trim(f"{t} band {y:.2f}", circle_y(1.07 * r, y, 20), 0.015, M["trim"], closed=True))
    for i in range(6):
        a = i / 6 * TAU + math.pi / 6
        bar = [Vector((math.sin(a) * rr, y, math.cos(a) * rr)) for y, rr in
               ((0.06, 1.02 * r), (h * 0.5, 1.07 * r), (h - 0.08, 1.02 * r))]
        add(tube(f"{t} strut {i}", bar, [0.024 * (r / 0.3) ** 0.5] * 3, [M["iron"]], n=6, per=4))
        if i % 2 == 0:
            add(gem(f"{t} rivet {i}", Vector((math.sin(a) * 1.23 * r, -0.01, math.cos(a) * 1.23 * r)), 0.018,
                    M["glow"], (1, 1, 1)))
    # 顶部阀门与手轮
    vh = h + 0.27
    add(lathe_y(f"{t} valve", [(0.075, vh - 0.02), (0.075, vh + 0.16), (0.10, vh + 0.18), (0.10, vh + 0.22),
                               (0.002, vh + 0.23)], [M["gold"]], 16))
    add(trim(f"{t} wheel", circle_y(0.15 * (r / 0.3) ** 0.5, vh + 0.13, 18), 0.016, M["trim"], closed=True))
    for i in range(4):
        a = i / 4 * TAU
        w = 0.15 * (r / 0.3) ** 0.5
        add(tube(f"{t} spoke {i}", [Vector((0, vh + 0.13, 0)), Vector((math.sin(a) * w, vh + 0.13, math.cos(a) * w))],
                 [0.010, 0.010], [M["gold"]], n=5, per=1))
    add(gem(f"{t} valve gem", Vector((0, vh + 0.235, 0)), 0.030, M["glow"], (1, 1, 1)))
    return mw


def build_pipe(ctx, M, name, pts, r, spec=None):
    """铁质管路 + 两端金接头 + 中段发光观察窗。"""
    spec = spec or rigid("Chest")
    ctx.part(tube(name, pts, [r] * len(pts), [M["iron"]], n=10, per=6), spec)
    P, _ = catmull([Vector(p) for p in pts], [r] * len(pts), 6)
    m = len(P)
    for f in (0.02, 0.98):
        i = min(m - 2, int(f * (m - 1)))
        d = (P[i + 1] - P[i]).normalized()
        a, b = P[i] - d * 0.05, P[i] + d * 0.05
        ctx.part(tube(name + f" coupling {f}", [a, b], [r * 1.35, r * 1.35], [M["gold"]], n=10, per=1), spec)
    for f in (0.35, 0.62):
        i = min(m - 2, int(f * (m - 1)))
        d = (P[i + 1] - P[i]).normalized()
        a, b = P[i] - d * 0.07, P[i] + d * 0.07
        ctx.part(tube(name + f" window {f}", [a, b], [r * 1.12, r * 1.12], [M["venom"]], n=10, per=1), spec)
        for e in (a, b):
            ctx.part(tube(name + f" window rim {f}{e.x:.2f}", [e - d * 0.012, e + d * 0.012], [r * 1.25, r * 1.25],
                          [M["gold"]], n=10, per=1), spec)
