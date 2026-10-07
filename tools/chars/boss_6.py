"""Boss 6 · 剧毒三位体 · 毒素九头蛇（Venom Trinity · Toxic Hydra）。

设定：约 5 m 高的三首机械蛇。翠黑雕花漆甲躯体伏在四条短粗机械腿上，尾部盘向右后方；背负三只发绿光的
毒液储罐（金笼架 + 铁管路接入三条颈根），胸前一枚毒液反应核；三条长颈（各 7 节骨蒙皮：鳞甲皮、背侧叠甲、
腹侧发光毒管、关节金箍、颈根三层扇贝颈甲）各接一颗蝰蛇形机械头：分层兜帽鳍与锯齿中冠（主首另有金角）、
狭长发光眼、颊部毒腺、象牙毒牙挂着发光毒滴。
动作：Idle（三颈错相游移）/ Move（沉重爬行：四足依次落地、躯干左右摆、三颈错相摆动）/
Attack（三首后仰蓄力，再同时前探喷出扇形毒雾）/ Enrage（盘颈蓄势后仰天咆哮、三颈甩动，储罐亮度拉高）。
网页驱动节点：无（储罐爆亮、毒雾、毒滴都由骨骼缩放关键帧完成：Surge0-2 / Spray{L,C,R} / Drip{L,C,R}）。
毒雾特效（2026-10-01 重做）：旧版是不透明薄片 + 小球，现为半透明毒雾羽流（雾片扇面 + 湍流雾壳 + 喷流芯 + 喷口光晕）与水滴形毒滴，
单一图集材质（BLEND、强度 2.0），见 _b6fx_spray.py / _b6fx_maps.py；Spray 骨名与缩放驱动不变。
"""

import math
import os

from mathutils import Matrix, Vector

from kit.core import (TAU, clamp, filigree_maps, finish, fn, frame_from, lerp, orient, rigid, scale_maps,
                      smoothstep, spike, surface, transform, tube)
from kit.rig import R, X, Y, Z

from chars import _b6fx_spray as FX
from chars._b6_kit import (Spine, blob, chain_dorsals, clearance_check, closeup, frame_matrix, ground_check, lathe_y, loop,
                           orth, rot, sampled, seam_check, sgnpow, solve_chain, spine_shell, stats, surf_normal,
                           track, venom_maps, with_defaults)
from chars._b6_parts import (SPRAY_K, build_head, build_leg, build_neck, build_pipe, build_tail, build_tank, gem,
                             tank_matrix, trim)

TITLE = "Venom Trinity"
ACCENT = (0.55, 0.86, 0.70)
CLIPS = ("Idle", "Move", "Attack", "Enrage")
GAME_TRIS = 85000
LOD_KEEP = ("inlay", "glow", "hem", "trim", "core")
REVIEW_POSE = ("Idle", 1)
TOXIC = (0.42, 1.0, 0.60)
NECKS = "LCR"
SIDE = {"L": -1, "C": 0, "R": 1}
PHASE = {"L": 0.0, "C": TAU / 3, "R": 2 * TAU / 3}


# ===== 材质 =====
def materials(ctx):
    M = ctx.M
    ctx.mat("armor", "jade lacquer armor", (0.028, 0.052, 0.046), metal=0.6, rough=0.30, coat=0.5)
    ctx.texture("armor", filigree_maps((0.030, 0.058, 0.050), (0.085, 0.190, 0.140), size=1024, seed=6, density=22,
                                       width=1), normal_strength=0.35)
    ctx.mat("scale", "serpent scale hide", (0.02, 0.05, 0.04), metal=0.35, rough=0.38, coat=0.3)
    ctx.texture("scale", scale_maps((0.030, 0.085, 0.066), (0.30, 0.55, 0.36), emit_rgb=(0.10, 0.34, 0.20), size=1024,
                                    rows=8), emit_strength=1.2, normal_strength=0.8)
    ctx.mat("gold", "verdigris gold", (0.80, 0.62, 0.30), metal=1.0, rough=0.28)
    ctx.mat("trim", "gold trim", (0.84, 0.66, 0.32), metal=1.0, rough=0.24)
    ctx.mat("iron", "gunmetal pipework", (0.060, 0.070, 0.070), metal=0.95, rough=0.32)
    ctx.mat("fang", "venom ivory", (0.80, 0.78, 0.66), rough=0.35, coat=0.3)
    ctx.mat("venom", "venom tank core", (0.10, 0.42, 0.18), emit=TOXIC, strength=2.2)
    ctx.texture("venom", venom_maps(TOXIC, size=512), emit_strength=2.2, normal_strength=0.3)
    ctx.mat("surge", "venom surge glow", (0.35, 1.0, 0.5), emit=(0.30, 1.0, 0.45), strength=5.0)
    ctx.mat("glow", "toxic glow", (0.4, 0.95, 0.55), emit=(0.32, 1.0, 0.50), strength=6.0)
    ctx.mat("inlay", "venom inlay", (0.25, 0.65, 0.40), emit=TOXIC, strength=2.8)
    # 毒雾：半透明图集材质（外 / 内雾壳 + 喷流芯 + 雾片 + 毒滴 + 喷口光晕），强度 <= 2.5，见 _b6fx_spray / _b6fx_maps
    M["spray"] = FX.spray_material(f"{ctx.title} venom spray glow")
    return M


# ===== 躯体（超椭球舰体：s=cos φ 沿身长，a 绕身轴，a=0 为背） =====
BODY_C = Vector((0, -0.15, 1.40))
HY0, HLY = -0.15, 1.52


def hull_dims(s):
    w = 1.04 - 0.12 * s * s - 0.10 * max(0.0, -s)
    ht = 0.60 + 0.10 * max(0.0, s)
    return w, ht, 0.50, 1.40 + 0.14 * s


def hull_at(a, phi):
    s = math.cos(phi)
    rho = max(0.0, math.sin(phi)) ** 0.5
    w, ht, hb, zc = hull_dims(s)
    ca, sa = math.cos(a), math.sin(a)
    x = w * rho * sgnpow(sa, 2 / 2.6)
    z = zc + (ht if ca >= 0 else hb) * rho * sgnpow(ca, 2 / 2.6)
    return Vector((x, HY0 + HLY * s, z))


def phi_of(y):
    return math.acos(clamp((y - HY0) / HLY, -1, 1))


def hull_off(a, phi, extra):
    ref = Vector((0, HY0 + HLY * math.cos(phi), hull_dims(math.cos(phi))[3]))
    return hull_at(a, phi) + surf_normal(hull_at, a, phi, ref) * extra


def body_w(p):
    """躯干蒙皮：前段（含四腿根、储罐）全归 Chest，尾根一段过渡到 Pelvis。"""
    w = smoothstep(-1.45, -0.95, p.y)
    return {"Chest": w, "Pelvis": 1 - w}


BODY = fn(body_w)


def build_body(ctx, M):
    t = ctx.title
    hull = surface(f"{t} hull", lambda u, v: hull_at(u * TAU, v * math.pi), 80, 60, [M["scale"]], closed_u=True,
                   uvfn=lambda u, v: (u * 4, v * 3))
    ctx.part(orient(hull, lambda c: Vector((0, c.y, 1.5))), BODY)
    # 背甲：五道拱形叠甲（后缘翘起压住下一道），金边 + 嵌线
    A = 1.34
    bands = [(0.60, 0.08), (0.16, -0.36), (-0.28, -0.80), (-0.72, -1.18), (-1.10, -1.52)]
    for k, (y0, y1) in enumerate(bands):
        p0, p1 = phi_of(y0), phi_of(y1)
        off0, off1 = 0.035, 0.090

        def pp(u, v, p0=p0, p1=p1, off0=off0, off1=off1, extra=0.0):
            a = lerp(-A, A, u)
            return hull_off(a, lerp(p0, p1, v), lerp(off0, off1, v ** 1.5) + 0.02 * math.sin(math.pi * u) + extra)
        sh = surface(f"{t} carapace {k}", pp, 36, 12, [M["armor"]], uvfn=lambda u, v: (u * 2.5, v * 0.6))
        orient(sh, lambda c: Vector((0, c.y, 1.45)))
        ctx.part(finish(sh, 0.035, -1, 0), BODY)
        ctx.part(trim(f"{t} carapace edge {k}", [pp(i / 20, 1.0, extra=0.006) for i in range(21)], 0.018,
                      M["trim"]), BODY)
        for sd in (-1, 1):
            ctx.part(trim(f"{t} carapace side {k}{sd}", [pp(0.0 if sd < 0 else 1.0, i / 6, extra=0.006)
                                                          for i in range(7)], 0.014, M["trim"]), BODY)
            ctx.part(trim(f"{t} carapace inlay {k}{sd}", [pp(0.5 + sd * lerp(0.14, 0.40, i / 6), 0.82, extra=0.004)
                                                          for i in range(7)], 0.009, M["inlay"]), BODY)
        if k >= 3:
            b = pp(0.5, 0.75)
            nrm = surf_normal(hull_at, 0.0, lerp(p0, p1, 0.75), Vector((0, b.y, 1.45)))
            h = 0.42 if k == 3 else 0.32
            ctx.part(spike(f"{t} dorsal spike {k}", b - nrm * 0.02, b + nrm * h + Vector((0, -h * 0.55, 0)), 0.09,
                           [M["gold"]], sides=8, bend=0.04, up=(0, -1, 0)), BODY)
    # 胸甲：包住吻端的前护甲（让出胸前反应核）
    def fp(u, v, extra=0.0):
        a = lerp(-2.05, 2.05, u)
        return hull_off(a, lerp(0.36, 0.66, v), lerp(0.03, 0.075, v) + extra)
    br = surface(f"{t} breastplate", fp, 44, 10, [M["armor"]], uvfn=lambda u, v: (u * 3, v * 0.5))
    orient(br, lambda c: Vector((0, c.y, 1.6)))
    ctx.part(finish(br, 0.03, -1, 0), BODY)
    for v in (0.0, 1.0):
        ctx.part(trim(f"{t} breast edge {v}", [fp(i / 28, v, 0.006) for i in range(29)], 0.016, M["trim"]), BODY)
    build_reactor(ctx, M)
    build_vials(ctx, M)
    # 腹甲：三道横向金箍护住下腹
    for k, y in enumerate((0.55, 0.0, -0.55)):
        p = phi_of(y)
        ctx.part(trim(f"{t} belly band {k}", [hull_off(math.pi + lerp(-1.25, 1.25, i / 16), p, 0.01)
                                             for i in range(17)], 0.02, M["trim"]), BODY)


REACTOR_C = Vector((0, 1.36, 1.48))
REACTOR_N = Vector((0, 1, -0.18)).normalized()


def build_reactor(ctx, M):
    """胸前毒液反应核：金框 + 毒液穹顶 + 八道金笼肋 + 十二道放射金芒 + 发光环。"""
    t = f"{ctx.title} reactor"
    mw = frame_matrix(REACTOR_C, REACTOR_N, (0, 0, 1))

    def add(obj):
        transform(obj, mw)
        ctx.part(obj, BODY)
    add(lathe_y(f"{t} frame", [(0.36, -0.12), (0.38, 0.0), (0.36, 0.05), (0.29, 0.075), (0.26, 0.03)],
                [M["gold"]], 48))
    add(lathe_y(f"{t} core", [(0.265, -0.06), (0.265, 0.0), (0.21, 0.07), (0.11, 0.115), (0.002, 0.13)],
                [M["venom"]], 32, uv=lambda u, v: (u * 2, v)))
    for i in range(8):
        a = i / 8 * TAU
        pts = [Vector((math.sin(a) * r, y, math.cos(a) * r)) for r, y in
               ((0.28, 0.06), (0.22, 0.10), (0.12, 0.14), (0.03, 0.155))]
        add(tube(f"{t} rib {i}", pts, [0.012] * 4, [M["gold"]], n=6, per=4))
    add(gem(f"{t} heart", Vector((0, 0.16, 0)), 0.045, M["glow"], (1, 0.6, 1)))
    add(trim(f"{t} ring", [Vector((math.sin(a) * 0.41, 0.0, math.cos(a) * 0.41)) for a in
                           [i / 36 * TAU for i in range(36)]], 0.013, M["inlay"], closed=True))
    for i in range(12):
        a = i / 12 * TAU
        L = 0.24 if i % 3 == 0 else 0.13
        d = Vector((math.sin(a), 0, math.cos(a)))
        add(spike(f"{t} ray {i}", d * 0.37 + Vector((0, -0.02, 0)), d * (0.37 + L) + Vector((0, -0.06, 0)), 0.035,
                  [M["gold"]], sides=4, fx=1.0, fy=0.4, up=(0, 1, 0)))


def build_vials(ctx, M):
    """躯干两侧毒液弹药瓶：发光胶囊 + 金端盖 + 漆甲托架。"""
    t = f"{ctx.title} vial"
    for sd in (-1, 1):
        for k, y in enumerate((0.28, -0.14, -0.56)):
            p = phi_of(y)
            a = sd * (math.pi / 2 - 0.05)
            c = hull_off(a, p, 0.10)
            axis = (hull_at(a, phi_of(y - 0.05)) - hull_at(a, phi_of(y + 0.05))).normalized() * -1
            mw = frame_matrix(c, axis, (0, 0, 1))
            parts = [lathe_y(f"{t} glass {sd}{k}", [(0.002, -0.15), (0.068, -0.12), (0.068, 0.12), (0.002, 0.15)],
                             [M["venom"]], 12),
                     lathe_y(f"{t} cap a {sd}{k}", [(0.002, -0.20), (0.06, -0.20), (0.085, -0.17), (0.085, -0.11),
                                                    (0.07, -0.10)], [M["gold"]], 16),
                     lathe_y(f"{t} cap b {sd}{k}", [(0.07, 0.10), (0.085, 0.11), (0.085, 0.17), (0.06, 0.20),
                                                    (0.002, 0.20)], [M["gold"]], 16),
                     blob(f"{t} cradle {sd}{k}", (-sd * 0.07, 0, 0), (0.07, 0.16, 0.06), [M["armor"]], 12, 8,
                          power=2.6)]
            for o in parts:
                transform(o, mw)
                ctx.part(o, BODY)


# ===== 静止骨架数据 =====
NECK_DEF = {
    "C": dict(root=(0.0, 0.62, 2.05), t0=(0.0, 0.22, 1.0), head=(0.0, 1.92, 4.28), hd=(0.0, 1.0, -0.30), L=3.45,
              r=(0.29, 0.20), hs=1.12, bow=(0.0, -0.12, 1.0)),
    "L": dict(root=(-0.70, 0.98, 1.83), t0=(-0.50, 0.30, 1.0), head=(-1.72, 1.72, 3.66), hd=(-0.36, 1.0, -0.26),
              L=3.00, r=(0.25, 0.18), hs=0.96, bow=(-0.5, -0.1, 1.0)),
}
NECK_DEF["R"] = {k: (tuple(-c if i == 0 else c for i, c in enumerate(v)) if k in ("root", "t0", "head", "hd", "bow")
                     else v) for k, v in NECK_DEF["L"].items()}
BONE_W = (1.14, 1.09, 1.04, 1.0, 0.96, 0.91, 0.86)
LEG_DEF = {
    "FL": dict(hip=(-0.72, 0.78, 1.22), knee=(-1.40, 1.00, 1.10), ankle=(-1.52, 1.14, 0.28), yaw=0.30),
    "BL": dict(hip=(-0.72, -0.86, 1.18), knee=(-1.38, -1.06, 1.06), ankle=(-1.50, -1.16, 0.28), yaw=0.12),
}
TAIL_PTS = [(0.0, -1.35, 1.26), (0.02, -1.95, 0.92), (0.22, -2.48, 0.58), (0.70, -2.86, 0.42), (1.32, -2.92, 0.33),
            (1.86, -2.58, 0.31), (2.08, -2.02, 0.31)]
TAIL_R = [0.42, 0.35, 0.28, 0.23, 0.18, 0.13, 0.08]
TANKS = [dict(base=(-0.82, -0.76, 1.74), axis=(-0.34, -0.16, 0.93), r=0.27, h=1.10),
         dict(base=(0.0, -0.32, 1.88), axis=(0.0, -0.20, 0.98), r=0.38, h=1.45),
         dict(base=(0.82, -0.76, 1.74), axis=(0.34, -0.16, 0.93), r=0.27, h=1.10)]


def neck_rest(S):
    d = NECK_DEF[S]
    root, head = Vector(d["root"]), Vector(d["head"])
    t0, hd = Vector(d["t0"]).normalized(), Vector(d["hd"]).normalized()
    total = sum(BONE_W)
    lengths = [w / total * d["L"] for w in BONE_W]
    bow = Vector(d["bow"]).normalized()
    joints, s = solve_chain(root, t0, head, hd, lengths, bow)
    lengths = [(joints[j + 1] - joints[j]).length for j in range(len(lengths))]
    # 背侧取弯曲平面里背离弯曲方向的一侧（颈根处为后方，传到颈端即头顶）
    up0 = -orth(hd, t0)
    dors = chain_dorsals(joints, up0)
    fwd = (joints[-1] - joints[-2]).normalized()
    up_t = orth(dors[-1], hd)
    up_w = orth(Vector((0, 0, 1)), hd)
    up = orth(up_t.lerp(up_w, 0.6), hd)
    print(f"NECK {S}: bow {s:.3f}  tip miss {(joints[-1] - head).length:.3f} m  "
          f"head-up twist {math.degrees(up_t.angle(up_w)):.1f} deg  tip-dir {math.degrees(fwd.angle(hd)):.1f} deg")
    return {"bones": [f"Neck{S}{j}" for j in range(1, 8)], "joints": joints, "lengths": lengths, "dors": dors,
            "up0": up0, "t0": t0, "hd": hd, "O": joints[-1].copy(), "up": up, "lat": hd.cross(up).normalized(),
            "r": d["r"], "hs": d["hs"], "king": S == "C", "bow": bow}


def leg_rest():
    legs = {}
    for label, d in LEG_DEF.items():
        for sd, side_l in ((-1, "L"), (1, "R")):
            lab = label[0] + side_l

            def mir(v, sd=sd):
                return Vector((v[0] if sd < 0 else -v[0], v[1], v[2]))
            H, K, A = mir(d["hip"]), mir(d["knee"]), mir(d["ankle"])
            yaw = d["yaw"] * (-sd)
            ball = A + rot(Vector((0, 0.42, -0.17)), (0, 0, 1), yaw)
            dirv = (A - H).normalized()
            kp = K - H
            pole = (kp - dirv * kp.dot(dirv)).normalized()
            legs[lab] = {"hip": H, "knee": K, "ankle": A, "ball": ball, "side": sd, "body": "Chest", "pole": pole,
                         "fdir": (ball - A).normalized()}
    return legs


# ===== 构建 =====
def build(ctx):
    M = materials(ctx)
    necks = {S: neck_rest(S) for S in NECKS}
    legs = leg_rest()
    build_body(ctx, M)
    for label, L in legs.items():
        build_leg(ctx, M, label, L)
        build_pauldron(ctx, M, label, L)
    tail_pts = [Vector(p) for p in TAIL_PTS]
    build_tail(ctx, M, tail_pts, TAIL_R)
    for k, T in enumerate(TANKS):
        build_tank(ctx, M, k, {**T, "axis": Vector(T["axis"]).normalized(), "base": Vector(T["base"])})
    heads = {}
    for S in NECKS:
        N = necks[S]
        build_neck(ctx, M, S, N)
        heads[S] = build_head(ctx, M, S, {"O": N["O"], "fwd": N["hd"], "up": N["up"], "hs": N["hs"], "king": N["king"]})
    pipes = build_pipes(ctx, M, necks)
    stats(ctx, GAME_TRIS, LOD_KEEP, detail=bool(os.environ.get("B6_CLOSEUP")))
    if os.environ.get("B6_CLOSEUP"):
        hc = necks["C"]["O"] + necks["C"]["hd"] * 0.5
        hl = necks["L"]["O"] + necks["L"]["hd"] * 0.45
        closeup(ctx.id, [("head-c", hc + Vector((1.5, 2.3, 0.6)), hc, 55),
                         ("head-l", hl + Vector((-1.9, 1.2, 0.5)), hl, 55),
                         ("heads-top", Vector((0.5, 2.8, 8.0)), Vector((0, 1.9, 3.6)), 40),
                         ("tanks", Vector((-3.0, -4.2, 4.6)), Vector((0, -0.4, 2.4)), 42)], ACCENT)
    tail_lat = []
    for j in range(len(tail_pts) - 1):
        d = (tail_pts[j + 1] - tail_pts[j]).normalized()
        tail_lat.append(orth(d.cross(Vector((0, 0, 1))), d))
    return {"necks": necks, "legs": legs, "heads": heads, "tail_pts": tail_pts, "tail_lat": tail_lat,
            "pipes": pipes}


def build_pauldron(ctx, M, label, L):
    """髋肩甲：两层叠甲罩住腿根；内层随躯干，外层随大腿。"""
    H, K = L["hip"], L["knee"]
    d1 = (K - H).normalized()
    sp = Spine([H - d1 * 0.25, H.lerp(K, 0.5), K], [0.35, 0.33, 0.29], (0, 0, 1), per=4)
    t = f"{ctx.title} pauldron {label}"
    for k, (t0, t1, o0, o1, spec) in enumerate(((0.0, 0.42, 0.10, 0.17, BODY),
                                                (0.30, 0.70, 0.07, 0.12, rigid(f"Thigh.{label}")))):
        A = 1.55 - 0.15 * k
        sh = spine_shell(f"{t} {k}", sp, t0, t1, -A, A, o0, o1, [M["armor"]], 18, 8, arch=0.03)
        ctx.part(finish(sh, 0.03, -1, 0), spec)
        ctx.part(trim(f"{t} edge {k}", [sp.pt(t1, a, o1 + 0.03 * math.sin(math.pi * (a + A) / (2 * A)) + 0.004)
                                        for a in [lerp(-A, A, i / 12) for i in range(13)]], 0.015, M["trim"]), spec)
        if k == 0:
            ctx.part(trim(f"{t} inlay", [sp.pt(lerp(t0 + 0.05, t1 - 0.06, i / 5), 0.0, o0 + 0.05) for i in range(6)],
                          0.010, M["inlay"]), spec)


def build_pipes(ctx, M, necks):
    """储罐顶 → 颈根颈甲背面的主管路，侧罐另有一根下行管接入躯干侧面。返回静止胶囊（查穿插用）。"""
    caps = []
    for k, T in enumerate(TANKS):
        T = {**T, "axis": Vector(T["axis"]).normalized(), "base": Vector(T["base"])}
        mw = tank_matrix(T)
        caps.append((f"tank{k}", T["base"], T["base"] + T["axis"] * (T["h"] + 0.3), T["r"] * 1.25))
        S = "LCR"[k]
        if k == 1:
            # 中罐紧贴中颈根部（内部直连）；顶部两根管向左右下行接入背甲，避开中颈后仰 / 盘颈时的拱起空间
            for sd in (-1, 1):
                s = mw @ Vector((sd * 0.95 * T["r"], T["h"] + 0.02, 0.0))
                e = hull_off(sd * 0.62, phi_of(-0.05), -0.02)
                m1 = s + Vector((sd * 0.30, 0.05, -0.22))
                m2 = e + Vector((0, -0.05, 0.28))
                pts = [s, m1, m2, e]
                build_pipe(ctx, M, f"{ctx.title} pipe {k}{sd}", pts, 0.050)
                for a, b in zip(pts, pts[1:]):
                    caps.append((f"pipe{k}{sd}", a, b, 0.065))
            continue
        N = necks[S]
        c0, T0 = N["joints"][0], N["t0"]
        D0 = orth(N["up0"], T0)
        r0 = N["r"][0]
        inward = Vector((-SIDE[S] * 0.35, 0, 0))
        end = c0 + T0 * 0.02 + (D0 + inward).normalized() * (r0 * 1.36)
        start = mw @ Vector((-SIDE[S] * 0.35 * T["r"], T["h"] + 0.08, -0.95 * T["r"]))
        fwd = (end - start)
        mid1 = start + Vector((0, 0.18, 0.10)) + fwd * 0.25
        mid2 = end + (D0 + inward).normalized() * 0.30 + Vector((0, 0, 0.18))
        pts = [start, mid1, mid2, end]
        build_pipe(ctx, M, f"{ctx.title} pipe {k}", pts, 0.046)
        for a, b in zip(pts, pts[1:]):
            caps.append((f"pipe{k}", a, b, 0.065))
        sd = SIDE[S]
        s2 = mw @ Vector((sd * 0.9 * T["r"], T["h"] * 0.82, 0.0))
        e2 = hull_off(sd * 1.05, phi_of(-0.35), -0.02)
        m2 = s2 + Vector((sd * 0.22, 0.05, -0.18))
        build_pipe(ctx, M, f"{ctx.title} side pipe {k}", [s2, m2, e2.lerp(m2, 0.35), e2], 0.040)
    return caps


# ===== 骨骼 =====
def skeleton(rig, st):
    rig.bone("Root", (0, 0, 0), (0, 0, 0.5), roll=Y)
    rig.bone("Hover", (0, 0, 0.5), (0, 0, 1.0), "Root", roll=Y)
    rig.translate["Hover"] = "_hover"
    rig.bone("Pelvis", BODY_C, (0, -1.30, 1.44), "Hover", roll=Z)
    rig.bone("Chest", BODY_C, (0, 1.10, 1.70), "Hover", roll=Z)
    for label, L in st["legs"].items():
        rig.bone(f"Thigh.{label}", L["hip"], L["knee"], L["body"], roll=Z)
        rig.bone(f"Shin.{label}", L["knee"], L["ankle"], f"Thigh.{label}", roll=Y)
        rig.bone(f"Foot.{label}", L["ankle"], L["ball"], f"Shin.{label}", roll=Z)
    rig.chain("Tail", st["tail_pts"], "Pelvis", roll=Z)
    for S in NECKS:
        N = st["necks"][S]
        H = st["heads"][S]
        dors = N["dors"]
        rig.chain(f"Neck{S}", N["joints"], "Chest", roll=lambda j, dors=dors: dors[j - 1])
        rig.bone(f"Head{S}", N["O"], N["O"] + N["hd"] * 0.7 * N["hs"], f"Neck{S}7", roll=N["up"])
        rig.bone(f"Jaw{S}", H["hinge"], H["jaw_tail"], f"Head{S}", roll=N["up"])
        rig.bone(f"Drip{S}", H["drip"][0], H["drip"][1], f"Head{S}", roll=N["hd"])
        rig.bone(f"Spray{S}", H["spray"][0], H["spray"][1], f"Head{S}", roll=N["up"])
    for k, T in enumerate(TANKS):
        base, axis = Vector(T["base"]), Vector(T["axis"]).normalized()
        rig.bone(f"Surge{k}", base, base + axis * 0.5, "Chest", roll=(0, -1, 0))
    rig.scaled = [f"Surge{k}" for k in range(3)] + [f"Drip{S}" for S in NECKS] + [f"Spray{S}" for S in NECKS]


# ===== 姿态合成 =====
def base_q():
    q = {"hover": (0.0, 0.0, 0.0), "chest": (0.0, 0.0, 0.0), "pelvis": (0.0, 0.0, 0.0),
         "tail_yaw": (0.0,) * 6, "tail_pitch": (0.0,) * 6, "thrash": 0.0}
    for S in NECKS:
        q.update({f"off.{S}": (0.0, 0.0, 0.0), f"yaw.{S}": 0.0, f"pitch.{S}": 0.0, f"jaw.{S}": 0.06,
                  f"spray.{S}": 0.0, f"drip.{S}": 0.3})
    for label in ("FL", "FR", "BL", "BR"):
        q[f"foot.{label}"] = (0.0, 0.0, 0.0, 0.0)
    for k in range(3):
        q[f"surge{k}"] = 0.98
    return q


def pose_neck(rig, st, p, S, q):
    """颈链：头部目标（躯干局部偏移）+ 头朝向（俯仰 / 偏航）→ 贝塞尔求关节 → 逐节 aim（背侧平行传输控制滚转）。"""
    N = st["necks"][S]
    ch0 = rig.SEG["Chest"][0]
    chh = rig.head(p, "Chest")
    dC = rig.delta(p, "Chest")
    head = chh + dC @ (N["O"] + Vector(q[f"off.{S}"]) - ch0)
    hd = rot(N["hd"], N["lat"], q[f"pitch.{S}"])
    hd = dC @ rot(hd, (0, 0, 1), q[f"yaw.{S}"])
    t0 = dC @ N["t0"]
    root = rig.head(p, N["bones"][0])
    joints, _ = solve_chain(root, t0, head, hd, N["lengths"], dC @ N["bow"])
    dors = dC @ N["dors"][0]
    d = t0
    for j, name in enumerate(N["bones"]):
        d = (joints[j + 1] - joints[j]).normalized()
        dors = orth(dors, d)
        rig.aim(p, name, d, up=dors, rest_up=N["dors"][j])
    last = (N["joints"][-1] - N["joints"][-2]).normalized()
    fr, fp = frame_from(last, N["dors"][-1]), frame_from(d, dors)
    up = orth(fp @ fr.transposed() @ N["up"], hd)
    rig.aim(p, f"Head{S}", hd, up=up, rest_up=N["up"])
    p[f"Jaw{S}"] = R((N["lat"], -q[f"jaw.{S}"]))


def tail_ground(rig, st, p, q):
    """躯体下沉 / 起伏会把贴地的尾尖压进地面：给 Tail2 追加俯仰（割线法两次），让尾尖回到静止高度。"""
    target = st["tail_pts"][-1].z + q.get("tail_tip", 0.0)
    ax = st["tail_lat"][1]
    pitch = q["tail_pitch"][1]

    def put(c):
        p["Tail2"] = R((ax, pitch + c), (Z, q["tail_yaw"][1]))
        return rig.tail(p, "Tail6").z
    c0, z0 = 0.0, put(0.0)
    c1, z1 = 0.04, put(0.04)
    for _ in range(2):
        if abs(z1 - z0) < 1e-7:
            break
        c2 = c1 + (target - z1) * (c1 - c0) / (z1 - z0)
        c0, z0 = c1, z1
        c1, z1 = c2, put(c2)


def compose(rig, st, q):
    p = {"_hover": Vector(q["hover"])}
    cx, cz, cy = q["chest"]
    p["Chest"] = R((X, cx), (Y, cy), (Z, cz))
    px, pz, py = q["pelvis"]
    p["Pelvis"] = R((X, px), (Y, py), (Z, pz))
    for label, L in st["legs"].items():
        dx, dy, dz, pitch = q[f"foot.{label}"]
        target = L["ankle"] + Vector((dx, dy, dz))
        dB = rig.delta(p, L["body"])
        f = dB @ L["fdir"]
        h = Vector((f.x, f.y, 0)).normalized()
        vz = L["fdir"].z
        fd = h * math.sqrt(max(0.0, 1 - vz * vz)) + Vector((0, 0, vz))
        if pitch:
            fd = rot(fd, h.cross(Vector((0, 0, 1))), pitch)
        rig.ik2(p, f"Thigh.{label}", f"Shin.{label}", target, dB @ L["pole"], end=f"Foot.{label}", end_dir=fd,
                rest_pole=L["pole"])
    for j in range(6):
        p[f"Tail{j + 1}"] = R((st["tail_lat"][j], q["tail_pitch"][j]), (Z, q["tail_yaw"][j]))
    tail_ground(rig, st, p, q)
    for S in NECKS:
        pose_neck(rig, st, p, S, q)
    sc = {}
    for k in range(3):
        s = q[f"surge{k}"]
        sc[f"Surge{k}"] = (s, 1.0, s)
    for S in NECKS:
        sc[f"Drip{S}"] = (1.0, 1.0 + 0.8 * q[f"drip.{S}"], 1.0)
        sc[f"Spray{S}"] = 1.0 + (1.0 / SPRAY_K - 1.0) * max(0.0, q[f"spray.{S}"])
    p["_scale"] = sc
    return p


# ===== 动作参数 =====
def idle_q(t):
    q = base_q()
    q["hover"] = (0.0, 0.0, -0.015 + 0.015 * math.sin(t))
    q["chest"] = (0.012 * math.sin(t + 0.4), 0.015 * math.sin(t), 0.0)
    q["pelvis"] = (0.0, -0.012 * math.sin(t), 0.0)
    for S in NECKS:
        ph = PHASE[S]
        q[f"off.{S}"] = (0.10 * math.sin(t + ph), 0.06 * math.sin(t + ph + 1.3),
                         0.07 * math.sin(2 * t + ph) + 0.03 * math.sin(t + ph))
        q[f"yaw.{S}"] = 0.20 * math.sin(t + ph + 0.9)
        q[f"pitch.{S}"] = 0.05 * math.sin(2 * t + ph + 0.5)
        q[f"jaw.{S}"] = 0.06 + 0.06 * (0.5 + 0.5 * math.sin(2 * t + ph))
        q[f"drip.{S}"] = 0.5 + 0.5 * math.sin(2 * t + ph * 1.7)
    q["tail_yaw"] = tuple(0.05 * math.sin(t - 0.6 * j) for j in range(6))
    for k in range(3):
        q[f"surge{k}"] = 0.975 + 0.02 * math.sin(2 * t + k * 2.1)
    return q


GAIT = {"FL": 0.0, "BR": 0.25, "FR": 0.5, "BL": 0.75}


def move_q(t):
    """沉重爬行：四足按 左前→右后→右前→左后 依次迈步（每刻三足着地），躯干 S 形左右摆，三颈错相摆动。"""
    q = base_q()
    stance, stride, lift = 0.70, 0.60, 0.26
    shock = 0.0
    for label, ph in GAIT.items():
        u = (t / TAU + ph) % 1.0
        if u < stance:
            s = u / stance
            dy, dz, pitch = stride * (0.5 - s), 0.0, 0.0
        else:
            s = (u - stance) / (1 - stance)
            e = s * s * (3 - 2 * s)
            dy = stride * (-0.5 + e)
            dz = lift * math.sin(math.pi * s) ** 0.8
            pitch = -0.30 * math.sin(math.pi * s) + 0.12 * math.sin(math.pi * s) ** 4
        d = (u - 0.02) % 1.0
        shock += math.exp(-(min(d, 1 - d) / 0.05) ** 2)
        q[f"foot.{label}"] = (0.0, dy, dz, pitch)
    q["hover"] = (0.05 * math.sin(t), 0.0, -0.05 - 0.025 * shock + 0.01 * math.cos(2 * t))
    q["chest"] = (0.015 * math.cos(2 * t) - 0.01 * shock, 0.075 * math.sin(t), 0.035 * math.sin(t + 0.5))
    q["pelvis"] = (0.0, -0.05 * math.sin(t), -0.025 * math.sin(t + 0.5))
    q["tail_yaw"] = tuple(0.12 * math.sin(t - 0.75 * (j + 1) - 0.4) for j in range(6))
    q["tail_pitch"] = tuple(0.015 * math.sin(2 * t - 0.6 * j) for j in range(6))
    for S in NECKS:
        ph = PHASE[S]
        q[f"off.{S}"] = (0.17 * math.sin(t + ph), 0.05 + 0.05 * math.sin(2 * t + ph + 0.6),
                         -0.04 + 0.10 * math.sin(2 * t + ph))
        q[f"yaw.{S}"] = -0.07 * math.sin(t) + 0.14 * math.sin(t + ph + 1.1)
        q[f"pitch.{S}"] = -0.06 + 0.05 * math.sin(2 * t + ph)
        q[f"jaw.{S}"] = 0.10 + 0.04 * math.sin(2 * t + ph)
        q[f"drip.{S}"] = 0.5 + 0.5 * math.sin(2 * t + ph)
    for k in range(3):
        q[f"surge{k}"] = 0.98 + 0.015 * math.sin(4 * t + k)
    return q


def necks3(C, side, **kw):
    """三颈参数：C / side 为 (x, y, z) 偏移，侧颈 x 表示外张量（按左右取号）；kw 里 yaw_out 为侧首外转角，
    其他键（pitch / jaw / spray / drip）三颈共用。"""
    out = {}
    for S in NECKS:
        sd = SIDE[S]
        if sd == 0:
            out[f"off.{S}"] = tuple(C)
        else:
            out[f"off.{S}"] = (side[0] * sd, side[1], side[2])
        for k, v in kw.items():
            if k == "yaw_out":
                out[f"yaw.{S}"] = -sd * v
            else:
                out[f"{k}.{S}"] = v
    return out


def attack_keys():
    """三首齐喷：1 起势 → 9 三首后仰蓄力 → 12 前探张口 → 14 毒雾全开 → 21 扇面扫开 → 25 收雾 → 33 收势。"""
    base = idle_q(0.0)
    rear = {"hover": (0.0, -0.08, -0.04), "chest": (0.08, 0.0, 0.0), "surge0": 1.04, "surge1": 1.04, "surge2": 1.04,
            **necks3((0.0, -0.45, 0.55), (0.14, -0.45, 0.40), yaw_out=0.10, pitch=0.50, jaw=0.28, spray=0.0, drip=1.0)}
    lunge = {"hover": (0.0, 0.10, -0.08), "chest": (-0.07, 0.0, 0.0), "surge0": 1.09, "surge1": 1.09, "surge2": 1.09,
             **necks3((0.0, 0.72, -0.42), (0.05, 0.62, -0.38), yaw_out=0.42, pitch=-0.24, jaw=0.85, spray=0.40,
                      drip=0.0)}
    full = dict(lunge, **necks3((0.0, 0.80, -0.46), (0.10, 0.70, -0.42), yaw_out=0.48, pitch=-0.28, jaw=0.90,
                                spray=1.0, drip=0.0))
    sweep = dict(full, **necks3((0.0, 0.74, -0.44), (0.22, 0.66, -0.40), yaw_out=0.62, pitch=-0.24, jaw=0.86,
                                spray=1.0, drip=0.0))
    end = {"hover": (0.0, 0.03, -0.03), "chest": (-0.02, 0.0, 0.0), "surge0": 1.02, "surge1": 1.02, "surge2": 1.02,
           **necks3((0.0, 0.35, -0.22), (0.08, 0.30, -0.20), yaw_out=0.25, pitch=-0.15, jaw=0.45, spray=0.0,
                    drip=0.2)}
    return with_defaults(base, [(1, {}, "io"), (9, rear, "io"), (12, lunge, "back"), (14, full, "out"),
                                (21, sweep, "io"), (25, end, "in"), (33, {}, "io")])


def enrage_keys():
    """狂暴：1 → 8 盘颈蓄势 → 14 仰天咆哮（储罐爆亮）→ 18-36 三颈错相甩动 → 42 回落 → 49 收势。"""
    base = idle_q(0.0)
    coil = {"hover": (0.0, -0.05, -0.12), "chest": (-0.05, 0.0, 0.0), "surge0": 1.0, "surge1": 1.0, "surge2": 1.0,
            **necks3((0.0, -0.25, -0.40), (-0.10, -0.20, -0.32), yaw_out=-0.10, pitch=-0.25, jaw=0.08)}
    roar = {"hover": (0.0, -0.04, 0.02), "chest": (0.12, 0.0, 0.0), "surge0": 1.13, "surge1": 1.13, "surge2": 1.13,
            **necks3((0.0, -0.35, 0.55), (0.45, -0.25, 0.42), yaw_out=0.35, pitch=0.70, jaw=0.95, drip=1.0)}
    thrash = dict(roar, thrash=1.0, chest=(0.06, 0.0, 0.0), surge0=1.14, surge1=1.14, surge2=1.14,
                  **necks3((0.0, -0.10, 0.35), (0.35, -0.10, 0.30), yaw_out=0.20, pitch=0.35, jaw=0.80))
    settle = {"thrash": 0.0, "hover": (0.0, 0.0, -0.02), "chest": (0.02, 0.0, 0.0), "surge0": 1.03, "surge1": 1.03,
              "surge2": 1.03, **necks3((0.0, 0.0, 0.10), (0.05, 0.0, 0.08), yaw_out=0.05, pitch=0.05, jaw=0.20)}
    return with_defaults(base, [(1, {}, "io"), (8, coil, "io"), (14, roar, "out"), (18, thrash, "io"),
                                (36, thrash, "lin"), (42, settle, "io"), (49, {}, "io")])


def enrage_q(keys, f):
    q = track(keys, f)
    w = q["thrash"]
    if w > 1e-4:
        tau = f - 14
        om = TAU / 11
        for S in NECKS:
            ph = PHASE[S]
            ox, oy, oz = q[f"off.{S}"]
            q[f"off.{S}"] = (ox + w * 0.42 * math.sin(om * tau + ph), oy,
                             oz + w * 0.16 * math.sin(2 * om * tau + ph + 0.5))
            q[f"yaw.{S}"] += w * 0.40 * math.cos(om * tau + ph)
            q[f"jaw.{S}"] += w * 0.12 * math.sin(3 * om * tau + ph)
        cx, cz, cy = q["chest"]
        q["chest"] = (cx, cz + w * 0.05 * math.sin(om * tau), cy + w * 0.03 * math.sin(om * tau + 1.0))
        hx, hy, hz = q["hover"]
        q["hover"] = (hx + w * 0.04 * math.sin(om * tau), hy, hz)
        q["tail_yaw"] = tuple(w * 0.10 * math.sin(om * tau - 0.8 * (j + 1)) for j in range(6))
        for k in range(3):
            q[f"surge{k}"] += w * 0.015 * math.sin(f * 1.3 + k * 2.0)
    return q


def attack_q(keys, f):
    q = track(keys, f)
    for S in NECKS:
        if q[f"spray.{S}"] > 0:
            q[f"spray.{S}"] *= 1.0 + 0.06 * math.sin(f * 1.9 + PHASE[S])
    return q


# ===== 动作 =====
def animate(rig, st):
    loop(rig, "Idle", 72, lambda t: compose(rig, st, idle_q(t)), step=2)
    loop(rig, "Move", 32, lambda t: compose(rig, st, move_q(t)), step=1)
    ak = attack_keys()
    sampled(rig, "Attack", 32, lambda f: compose(rig, st, attack_q(ak, f)))
    ek = enrage_keys()
    sampled(rig, "Enrage", 48, lambda f: compose(rig, st, enrage_q(ek, f)))
    checks(rig, st)
    spec = os.environ.get("B6_CLOSEUP_POSES")
    if spec:
        import bpy
        for item in spec.split(","):
            clip, f = item.split(":")
            rig.obj.animation_data.action = bpy.data.actions[clip]
            bpy.context.scene.frame_set(int(f))
            closeup(rig.ctx.id, [("heads", Vector((3.4, 7.6, 5.6)), Vector((0, 2.3, 3.4)), 36),
                                 ("top", Vector((0.4, 3.2, 10.5)), Vector((0, 2.2, 2.2)), 30)],
                    ACCENT, tag=f"{clip.lower()}{f}")


def checks(rig, st):
    feet = [f"Foot.{lb}" for lb in st["legs"]]
    ball_z = min(L["ball"].z for L in st["legs"].values())
    ground_check(rig, CLIPS, feet, offset=ball_z, label="foot (0 = planted)")
    ground_check(rig, CLIPS, [f"Tail{j}" for j in range(3, 7)], offset=lambda b: TAIL_R[int(b[4:]) - 1],
                 label="tail underside")
    seam_check(rig, ("Idle", "Move"))
    groups = {}
    for S in NECKS:
        N = st["necks"][S]
        r0, r1 = N["r"]
        groups[S] = [(b, lerp(r0, r1, j / 6) + 0.05) for j, b in enumerate(N["bones"]) if j >= 1]
        groups[S].append((f"Head{S}", 0.30 * N["hs"]))
    clearance_check(rig, CLIPS, groups, st["pipes"])
