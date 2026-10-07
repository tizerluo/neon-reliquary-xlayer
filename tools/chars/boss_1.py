"""Boss 1 · 苍白巨龙 · 低温暴君（Pale Wyrm · Cryogenic Tyrant）—— 第三轮（2026-10-01 复审返工：重做龙翼）。

设定：悬空盘绕的机械蛇龙。约 14.6 m 长的分节躯干（11 节躯干骨 + 核心 + 3 节颈 + 头，共 16 节脊骨）盘成一圈向上升起成粗壮的胸颈。
三层材质拉开：亮银叠瓦鳞（背，真实起伏的几何，每排错位半片）/ 深冰蓝分节腹板与头骨底（腹）/ 青色发光缝（节间环、板缝、眼缝、翼脉）。
每节之间一条银甲环 + 环心青光线；背脊一路是玻璃质刻面冰晶簇；机械龙首（放大到 1.7 倍，冠角后掠略收以便翼臂上扬）：
分段颌甲、可开合下颚带冰牙、发光眼缝、三层后掠头冠角、玻璃质“冰核王冠”+ 旋转银环；喉部两枚冰核在吐息时放大增亮；
身周一圈刻面冰棱缓慢环绕。吐息本身是游戏内特效，模型不带吐息几何，只留口部挂点骨 `Breath`。

第三轮重点（见 _b1r3_wing / _b1r3_body）：
- 龙翼：肩（银甲轴毂 + 冰核）→ 粗壮肱骨 → 肘 → 前臂主翼骨 → 腕（拇指冰爪）→ 5 根长指骨扇形展开，半透明冰蓝翼膜张在指骨之间并连到躯干，
  后缘扇形内凹的蝙蝠翼轮廓，翼脉发光；完全展开时单侧翼展（躯干侧面到翼尖冰爪）约 6.2 m，约为躯干宽度（≈1.95 m）的 3.2 倍，两翼合计约 14.4 m。静止几何 = 完全展开。
- 盘身：叠瓦鳞片几何 + 单元贴图、深冰蓝腹板、宽环板式节间银甲环。
动作：Idle（半展开，翼缓慢呼吸式起伏）/ Move（沿脊骨的行波蜿蜒 + 明显振翼）/ Attack（昂首蓄气时双翼向前包拢 → 头颈前探、张颚吐息，
双翼猛然向后展开）/ Enrage（盘身收紧、双翼裹拢 → 怒张到极限、王冠爆开）。
翼的动作参数：wlift 上扬、wsweep 前兜、close 指骨收拢、elbow 肘弯、wrist 指骨后掠、wtwist 旋前；用 _b1r3_check.py 逐帧查穿插。
"""

import math

from mathutils import Matrix, Vector

from kit.core import TAU, auto_smooth, clamp, fn, frost_maps, hex_maps, join, lerp, orient, plate, rigid, smoothstep, \
    surface
from kit.rig import R, X, Y, Z

from chars._bossA_common import (KDWeights, blob, bbox_report, interval_weights, loop, panel_maps, register_chains,
                                 resample, sampled, seam_check, studs, sweep, track, with_defaults, ground_check)
from chars._b1r2_parts import crystal_maps, crystals, hull_patch
from chars._b1r3_body import belly_tile, scale_tile
from chars._b1r3_wing import gem, trim, WingGeo, build_wing, membrane_maps, membrane_material, wing_axes

TITLE = "Pale Wyrm"
ACCENT = (0.61, 0.94, 1.0)
CLIPS = ("Idle", "Move", "Attack", "Enrage")
GAME_TRIS = 88000
LOD_KEEP = ("glow", "core", "crystal", "trim", "maw", "membrane")
REVIEW_POSE = ("Idle", 1)
CYAN = (0.40, 0.88, 1.0)

# 脊骨控制点：尾尖 → 头根（米）。尾巴在左前方上卷，身体向右后方盘一圈再升起成直立胸颈。
CTRL = [(-2.30, 1.30, 2.35), (-2.15, 0.85, 1.75), (-2.00, 0.15, 1.30), (-2.00, -0.95, 1.12), (-1.25, -2.05, 1.15),
        (0.00, -2.50, 1.25), (1.30, -2.05, 1.45), (2.00, -0.90, 1.75), (1.75, 0.15, 2.15), (0.90, 0.60, 2.65),
        (0.25, 0.50, 3.20), (0.00, 0.25, 3.85), (0.00, 0.20, 4.50), (0.00, 0.45, 5.05), (0.00, 0.95, 5.42),
        (0.00, 1.45, 5.52)]
CHEST = 11           # CTRL 下标：胸核（翼根）
RADII = [0.08, 0.22, 0.34, 0.44, 0.53, 0.61, 0.68, 0.74, 0.79, 0.84, 0.88, 0.92, 0.86, 0.78, 0.70, 0.66]
BODY = [f"Spine0.{j}" for j in range(1, 12)]     # 胸 → 尾
NECK = ["Neck1", "Neck2", "Neck3"]

# 龙首标架：头根 HB、朝向 HF（略向下）、头长 HL（后脑到吻尖）
HB = Vector(CTRL[-1])
HF = Vector((0.0, 0.965, -0.26)).normalized()
HU = (Vector((0, 0, 1)) - HF * HF.z).normalized()
HS_ = HF.cross(HU).normalized()                 # 头部侧向（+X）
HL = 2.55
BACK = HB - HF * 0.55
HORN_BACK, HORN_UP = 0.78, 0.90   # 冠角后掠 / 上扬缩放：翼臂上扬时要绕开冠角
HK = 1.7             # 龙首整体放大倍率（绕头根 HB；头部件按 1 倍建好后统一缩放）


def hk(p):
    return HB + (Vector(p) - HB) * HK


# ===== 材质 =====
def materials(ctx):
    M = ctx.M
    # 盘身三层：亮银叠瓦鳞（背）/ 深冰蓝分节腹板（腹）/ 青色发光缝；单元贴图与几何的鳞片一一对应
    ctx.mat("plate", "silver shingle scales", (0.70, 0.78, 0.86), metal=0.6, rough=0.42, coat=0.0)
    ctx.texture("plate", (*scale_tile(256, 3), None), emit_strength=1.0, normal_strength=0.0)
    ctx.mat("belly", "deep ice belly plates", (0.03, 0.09, 0.2), metal=0.4, rough=0.36, coat=0.25)
    ctx.texture("belly", (*belly_tile(256, 5), None), emit_strength=1.5, normal_strength=0.0)
    ctx.mat("under", "deep ice under-steel", (0.03, 0.08, 0.15), metal=0.85, rough=0.3, coat=0.3)
    ctx.texture("under", hex_maps(CYAN, base_rgb=(0.030, 0.080, 0.160), size=1024, cells=10, width=0.04),
                emit_strength=1.1, normal_strength=0.5)
    ctx.mat("lacq", "deep ice lacquer", (0.02, 0.06, 0.13), metal=0.6, rough=0.32, coat=0.5)
    ctx.texture("lacq", frost_maps((0.10, 0.60, 1.0), base_rgb=(0.02, 0.055, 0.12), size=1024, seed=9, branches=40),
                emit_strength=0.6, normal_strength=0.3)
    ctx.mat("armor", "polished silver armor", (0.80, 0.85, 0.90), metal=1.0, rough=0.26, coat=0.3)
    ctx.texture("armor", panel_maps((0.78, 0.83, 0.88), (0.04, 0.09, 0.17), (0.96, 0.98, 1.0), size=1024, cols=2,
                                    rows=2, seam=0.010, rivet=0.014, per=5), normal_strength=0.6)
    # 半透明冰蓝翼膜（两张变体贴图交替，避免左右翼 / 相邻翼膜花纹一样）
    rgba, em = membrane_maps(11, 1024)
    M["membrane"] = membrane_material(ctx, f"{ctx.title} ice membrane", rgba, em, 2.4)
    rgba, em = membrane_maps(23, 1024)
    M["membrane2"] = membrane_material(ctx, f"{ctx.title} ice membrane b", rgba, em, 2.4)
    # 玻璃质刻面冰晶：深冰蓝底、极低粗糙、满清漆、高反射，自发光只在根部与刻面中心（内部青光）
    ctx.mat("crystal", "glass ice crystal", (0.05, 0.16, 0.28), metal=0.0, rough=0.04, coat=1.0, spec=1.0)
    ctx.texture("crystal", crystal_maps(), emit_strength=3.2)
    ctx.mat("trim", "polished silver trim", (0.90, 0.93, 0.97), metal=1.0, rough=0.24)
    ctx.mat("dark", "blued gunmetal frame", (0.05, 0.08, 0.13), metal=0.95, rough=0.28)
    # 嵌线发光压低强度、提高饱和度：AgX 下过亮会褪成白色，失去青色
    ctx.mat("glow", "cryo inlay glow", (0.05, 0.45, 0.8), emit=(0.08, 0.60, 1.0), strength=2.0)
    ctx.mat("core", "ice core glow", (0.5, 0.9, 1.0), emit=(0.30, 0.80, 1.0), strength=6.0)
    ctx.mat("maw", "throat maw glow", (0.01, 0.03, 0.06), metal=0.6, rough=0.35)
    ctx.texture("maw", hex_maps((0.10, 0.62, 1.0), base_rgb=(0.010, 0.028, 0.060), size=512, cells=7, width=0.08),
                emit_strength=2.4, normal_strength=0.5)
    return M


# ===== 脊骨路径 =====
class Spine:
    """致密的脊骨路径：弧长 s、切向 T、背向 N（水平段取世界上方，竖直段取身后）、侧向 B、半径 r。"""

    def __init__(self):
        pts, rad = resample(CTRL, RADII, per=14)
        acc = [0.0]
        for i in range(1, len(pts)):
            acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
        self.L = acc[-1]
        n = int(self.L / 0.045)
        self.s = [self.L * i / n for i in range(n + 1)]
        self.p, self.r = [], []
        j = 0
        for s in self.s:
            while j < len(acc) - 2 and acc[j + 1] < s:
                j += 1
            t = (s - acc[j]) / max(1e-9, acc[j + 1] - acc[j])
            self.p.append(pts[j].lerp(pts[j + 1], t))
            self.r.append(lerp(rad[j], rad[j + 1], t))
        self.T, self.N, self.B = [], [], []
        for i, p in enumerate(self.p):
            d = self.p[min(i + 1, n)] - self.p[max(i - 1, 0)]
            T = d.normalized()
            w = smoothstep(0.5, 0.9, abs(T.z))
            up = (Vector((0, 0, 1)) * (1 - w) + Vector((0, -1, 0)) * w).normalized()
            N = (up - T * up.dot(T)).normalized()
            self.T.append(T)
            self.N.append(N)
            self.B.append(T.cross(N))
        # 控制点（关节）对应的弧长
        self.knot = []
        for c in CTRL:
            c = Vector(c)
            k = min(range(len(self.p)), key=lambda i: (self.p[i] - c).length)
            self.knot.append(self.s[k])

    def at(self, s):
        s = clamp(s, 0, self.L)
        i = min(len(self.s) - 2, int(s / self.L * (len(self.s) - 1)))
        t = (s - self.s[i]) / max(1e-9, self.s[i + 1] - self.s[i])
        lerpv = lambda a: a[i].lerp(a[i + 1], t)   # noqa: E731
        return lerpv(self.p), lerpv(self.T).normalized(), lerpv(self.N).normalized(), lerpv(self.B).normalized(), \
            lerp(self.r[i], self.r[i + 1], t)

    def idx(self, s):
        return int(round(clamp(s, 0, self.L) / self.L * (len(self.s) - 1)))

    def bounds(self):
        """[(骨名, s0, s1)]：弧长从尾到头排列。"""
        k = self.knot
        out = []
        for j, name in enumerate(BODY):              # Spine0.1 = 胸 → 下一节
            out.append((name, k[CHEST - j - 1], k[CHEST - j]))
        out.append(("Core", k[CHEST], k[CHEST + 1]))
        for j, name in enumerate(NECK):
            out.append((name, k[CHEST + 1 + j], k[CHEST + 2 + j]))
        out.append(("Head", k[-1], self.L + 5.0))
        return sorted(out, key=lambda b: b[1])

    def bone_at(self, s):
        for name, s0, s1 in self.bounds():
            if s0 - 1e-6 <= s <= s1 + 1e-6:
                return name
        return "Head"


SEG = 0.85            # 节间银甲环间距
A0 = 2.10             # 背甲 / 腹板分界角（背甲包到身侧）
HR = 0.050            # 叠瓦鳞片自由边翘起高度（占截面半径）
NSC = 10              # 背甲弧上横向鳞片数
NC = NSC * 4 + 1      # 背甲横向采样列数（每片鳞 4 列，错位行恰好差 2 列）
TPROF = (0.0, 0.12, 0.90)      # 每排鳞沿身长的采样位置（占一个鳞距）：自由边 / 高光肩 / 被压住端
PITCH_K, PITCH_MIN, PITCH_MAX = 0.30, 0.11, 0.28


def section(sp, i, a, belly=False, groove=True, lift=0.0):
    """第 i 个脊点处、角 a 的基础截面点（不含鳞片起伏）：背脊棱线 + 腹面压平；lift 为相对半径的外扩。"""
    p, N, Bv, r = sp.p[i], sp.N[i], sp.B[i], sp.r[i]
    return frame_pt(p, N, Bv, r, a, lift)


def frame_pt(p, N, Bv, r, a, lift=0.0, extra=0.0):
    rr = r * (1.0 + lift) + extra
    rr += 0.08 * r * math.exp(-(a / 0.28) ** 2) - 0.10 * r * math.exp(-((abs(a) - math.pi) / 0.9) ** 2)
    return p + N * (math.cos(a) * rr) + Bv * (math.sin(a) * rr * 1.06)


def hprof(t):
    """鳞片纵向轮廓：自由边（t=0）最高，在 t≈0.12 处圆润过肩，向头端线性压低到被压住端。"""
    return 1.0 - 0.05 * t / 0.12 if t < 0.12 else 0.95 * (1.0 - (t - 0.12) / 0.78) ** 1.1


def scale_rows(sp):
    """叠瓦行采样：[(s, t, q, 鳞距)]，每排 4 个采样（自由边 / 高光 / 中段 / 被压住端），鳞距随半径变化。"""
    rows = []
    s, q = 0.0, 0
    while s < sp.L - 1e-6:
        r = sp.r[sp.idx(s)]
        pitch = clamp(PITCH_K * r, PITCH_MIN, PITCH_MAX)
        for t in TPROF:
            if s + t * pitch < sp.L:
                rows.append((s + t * pitch, t, q, pitch))
        s += pitch
        q += 1
    rows.append((sp.L, 0.5, q, 1.0))
    return rows


def build_trunk(ctx, M, sp, kw):
    n = len(sp.p)
    head_cut = n - 1
    rows = scale_rows(sp)
    nv = len(rows)
    print(f"TRUNK rows {nv}, dorsal cols {NC}")
    # ----- 背甲：叠瓦鳞（每排错位半片，鳞片中线隆起、两侧收低；贴近背腹分界处起伏淡出以便与腹板无缝） -----
    def dorsal_pt(u, v):
        s, t, q, _ = rows[min(nv - 1, int(round(v * (nv - 1))))]
        j = int(round(u * (NC - 1)))
        a = -A0 + 2 * A0 * j / (NC - 1)
        uf = ((a + A0) / (2 * A0) * NSC + (0.5 if q % 2 else 0.0)) % 1.0
        env = 0.04 + 0.96 * math.cos(math.pi * (uf - 0.5)) ** 2
        fade = smoothstep(A0, A0 - 0.32, abs(a))
        p, T, N, Bv, r = sp.at(s)
        return frame_pt(p, N, Bv, r, a, HR * hprof(t) * env * fade)

    def dorsal_uv(u, v):
        s, t, q, _ = rows[min(nv - 1, int(round(v * (nv - 1))))]
        j = int(round(u * (NC - 1)))
        return (j / (NC - 1) * NSC + (0.5 if q % 2 else 0.0), q + t)
    obj = surface(f"{ctx.title} trunk dorsal", dorsal_pt, NC, nv, [M["plate"]], uvfn=dorsal_uv)
    orient(obj, lambda c: sp.p[min(range(0, n, 6), key=lambda k: (sp.p[k] - c).length)])
    auto_smooth(obj, 38)
    ctx.part(obj, fn(kw))
    # ----- 腹板：深冰蓝分节板（一排一块，板心微鼓，板缘一圈银蓝滚边，板缝青光） -----
    NB = 11

    def belly_pt(u, v):
        s, t, q, _ = rows[min(nv - 1, int(round(v * (nv - 1))))]
        a = A0 + (TAU - 2 * A0) * u
        p, T, N, Bv, r = sp.at(s)
        env = math.sin(math.pi * u) ** 0.7
        return frame_pt(p, N, Bv, r, a, 0.030 * hprof(t) * env - 0.012)

    def belly_uv(u, v):
        s, t, q, _ = rows[min(nv - 1, int(round(v * (nv - 1))))]
        return (u, q + t)
    obj = surface(f"{ctx.title} trunk belly", belly_pt, NB, nv, [M["belly"]], uvfn=belly_uv)
    orient(obj, lambda c: sp.p[min(range(0, n, 6), key=lambda k: (sp.p[k] - c).length)])
    ctx.part(obj, fn(kw))
    # ----- 两侧分界银线 + 腹部发光中线 -----
    for sd in (-1, 1):
        pts = [section(sp, i, sd * A0) + sp.B[i] * sd * 0.016 for i in range(2, head_cut, 6)]
        ctx.part(trim(f"{ctx.title} flank seam {sd}", pts, 0.020, M["trim"]), fn(kw))
    pts = [section(sp, i, math.pi, lift=0.022) - sp.N[i] * 0.004 for i in range(4, head_cut - 8, 4)]
    ctx.part(trim(f"{ctx.title} belly light", pts, 0.030, M["glow"]), fn(kw))
    # ----- 节间：银甲环（带棱的宽环板）+ 环心青光线 + 背甲铆钉 + 背甲盾片 -----
    k = 0
    s = SEG
    while s < sp.L - 0.9:
        r = sp.r[sp.idx(s)]
        if r > 0.14:
            build_collar(ctx, M, sp, kw, s, r, k)
            if r > 0.24:
                build_shield(ctx, M, sp, s, kw, k)
        k += 1
        s += SEG


def build_collar(ctx, M, sp, kw, s, r, k):
    """节间银甲环：沿身长 0.12 m 宽的环形甲带，中线隆起（两侧收低），环心嵌一圈青光线 + 背甲一排铆钉。"""
    w = 0.060 + 0.050 * r
    nu, nv_ = 28, 4

    def ring_pt(u, v):
        sv = s + (v - 0.5) * 2 * w
        p, T, N, Bv, rr = sp.at(sv)
        prof = math.sin(math.pi * v) ** 0.7
        return frame_pt(p, N, Bv, rr, u * TAU - math.pi, HR * 0.7, 0.004 + 0.014 * prof * (0.6 + rr))
    obj = surface(f"{ctx.title} segment collar {k}", ring_pt, nu, nv_, [M["trim"]], closed_u=True,
                  uvfn=lambda u, v: (u * 6, v))
    orient(obj, lambda c, s=s: sp.at(s)[0])
    ctx.part(obj, fn(kw))
    p, T, N, Bv, rr = sp.at(s)
    ring = [frame_pt(p, N, Bv, rr, q / 24 * TAU, HR * 0.7, 0.004 + 0.014 * (0.6 + rr) + 0.012) for q in range(24)]
    ctx.part(trim(f"{ctx.title} segment glow {k}", ring, 0.017 + 0.016 * r, M["glow"], closed=True), fn(kw))
    items = []
    for q in range(7):
        a = -1.75 + q / 6 * 3.5
        qp = frame_pt(p, N, Bv, rr, a, HR * 0.7, 0.004 + 0.014 * (0.6 + rr) + 0.010)
        items.append((qp, (qp - p).normalized(), 0.022 + 0.022 * r))
    ctx.part(studs(f"{ctx.title} segment rivets {k}", items, [M["trim"]], seg=6, rings=2), fn(kw))


def build_shield(ctx, M, sp, s, kw, k):
    """背甲盾片：每节背上一块深冰蓝漆甲，前宽后尖、贴合躯干弧度，银色包边 + 青色人字光纹。"""
    p, T, N, Bv, r = sp.at(s + 0.06)
    L = SEG * 0.86
    w0 = r * 0.62

    def half(x):
        return w0 * (1 - 0.55 * (x / L) ** 1.6)
    xs = [i / 10 * L for i in range(11)]
    outline = [(x, -half(x)) for x in xs] + [(L * 1.06, 0.0)] + [(x, half(x)) for x in reversed(xs)]
    origin = p + N * (r * 1.10 + 0.03)
    bulge = lambda x, y: -(y * y) / (2 * r * 1.05) + 0.07 * r * (x / L) ** 2   # noqa: E731
    sh = plate(f"{ctx.title} shield {k}", outline, 0.045, [M["lacq"]], origin=origin, xaxis=-T, yaxis=Bv,
               bulge=bulge, bev=0.01)
    ctx.part(sh, fn(kw))
    na = (-T).cross(Bv).normalized()
    edge = [origin - T * x + Bv * y + na * (bulge(x, y) + 0.026) for x, y in outline]
    ctx.part(trim(f"{ctx.title} shield trim {k}", edge + [edge[0]], 0.017, M["trim"], closed=True), fn(kw))
    vx = [(L * 0.74, -half(L * 0.74) * 0.60), (L * 0.20, 0.0), (L * 0.74, half(L * 0.74) * 0.60)]
    chev = [origin - T * x + Bv * y + na * (bulge(x, y) + 0.045) for x, y in vx]
    ctx.part(trim(f"{ctx.title} shield chevron {k}", chev, 0.020 + 0.010 * r, M["glow"], per=4), fn(kw))


def build_spines(ctx, M, sp):
    """背脊刻面冰晶簇：主晶 + 两侧副晶 + 小晶；胸背最高，向尾部与颈部渐小，尖端向尾部倾斜。"""
    s = 0.8
    k = 0
    chest_s = sp.knot[CHEST]
    while s < sp.knot[-1] - 0.35:
        p, T, N, Bv, r = sp.at(s)
        big = 0.28 + 0.95 * math.exp(-((s - chest_s + 1.6) / 3.3) ** 2) + 0.22 * math.exp(-((s - 5.0) / 2.5) ** 2)
        if s > chest_s:
            big *= 0.72
        base = p + N * r * 1.00
        d = (N - T * 0.55).normalized()
        alt = 1.0 if k % 2 == 0 else 0.78                # 大小交替，拉出节奏
        items = [(base - N * 0.10, base + d * big * alt, 0.075 + 0.075 * big * alt, 6)]
        for sd in (-1, 1):
            d2 = (d + Bv * sd * 0.55 - T * 0.1).normalized()
            b2 = base + Bv * sd * r * 0.30 - N * 0.07
            items.append((b2 - N * 0.05, b2 + d2 * big * 0.52 * alt, 0.045 + 0.04 * big, 6))
            d3 = (d + Bv * sd * 0.95 + T * 0.2).normalized()
            b3 = base + Bv * sd * r * 0.42 - N * 0.10 + T * 0.10
            items.append((b3 - N * 0.04, b3 + d3 * big * 0.26, 0.03 + 0.02 * big, 5))
        ctx.part(crystals(f"{ctx.title} spine {k}", items, [M["crystal"]], seed=k), rigid(sp.bone_at(s)))
        k += 1
        s += 0.44 if big > 0.6 else 0.52


def build_tail_blade(ctx, M, sp):
    """尾尖冰刃扇：五枚刻面冰晶 + 银箍 + 发光箍。"""
    p, T, N, Bv, r = sp.at(0.5)
    tip = sp.p[0]
    items = []
    for k, (ang, L) in enumerate(((0.0, 1.15), (0.5, 0.85), (-0.5, 0.85), (0.95, 0.55), (-0.95, 0.55))):
        d = (-T * math.cos(ang) + Bv * math.sin(ang) + N * 0.35).normalized()
        items.append((tip + T * 0.30, tip + d * L, 0.10 - 0.012 * k, 6))
    ctx.part(crystals(f"{ctx.title} tail blade", items, [M["crystal"]], seed=77), rigid(BODY[-1]))
    for q, (sv, mat, rad) in enumerate(((0.5, M["trim"], 0.028), (0.62, M["glow"], 0.02))):
        p, T, N, Bv, r = sp.at(sv)
        ring = [p + (N * math.cos(a) + Bv * math.sin(a)) * (r * 1.12 + 0.02) for a in [i / 20 * TAU for i in range(20)]]
        ctx.part(trim(f"{ctx.title} tail ring {q}", ring, rad, mat, closed=True), rigid(BODY[-1]))


# ===== 龙首 =====
def interp_(v, knots):
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if v <= x1:
            return lerp(y0, y1, clamp((v - x0) / (x1 - x0)))
    return knots[-1][1]


def sgnpow(x, k):
    return math.copysign(abs(x) ** k, x)


def prof(v):
    """头骨截面：半宽 w、上高 h、下深 d（上颌底到中轴）。后脑收圆、吻尖收尖。"""
    tip = 1 - 0.90 * smoothstep(0.92, 1.0, v)
    rear = math.sqrt(smoothstep(0.0, 0.12, v)) * 0.95 + 0.05
    k = tip * rear
    w = interp_(v, [(0, 0.46), (0.14, 0.62), (0.30, 0.64), (0.45, 0.50), (0.65, 0.40), (0.85, 0.33), (1.0, 0.22)])
    h = interp_(v, [(0, 0.40), (0.18, 0.50), (0.30, 0.46), (0.45, 0.30), (0.70, 0.21), (1.0, 0.12)])
    d = interp_(v, [(0, 0.34), (0.20, 0.24), (0.40, 0.15), (0.70, 0.11), (1.0, 0.07)])
    return w * k, h * k, d * k


def head_axis(v):
    return BACK + HF * (v * HL)


def skull_pt(a, v, lift=0.0):
    """上颅参数面：a=0 头顶，a>0 转向 +X 侧，a=π 上颌底；v 从后脑 0 到吻尖 1。"""
    w, h, d = prof(v)
    c, sn = math.cos(a), math.sin(a)
    e = 2 / (3.2 if c > 0 else 2.6)                  # 顶面更方：楔形扁吻
    # 眉脊：眼上方鼓起
    brow = 0.06 * math.exp(-((v - 0.32) / 0.08) ** 2) * math.exp(-((abs(sn) - 0.70) / 0.25) ** 2) * max(0.0, c)
    yy = sgnpow(c, e) * ((h + brow) if c > 0 else d)
    xx = sgnpow(sn, e) * w
    ax = head_axis(v)
    P = ax + HU * yy + HS_ * xx
    C = ax + HU * ((h - d) * 0.25)
    nrm = P - C
    nrm = nrm.normalized() if nrm.length > 1e-6 else HU
    return P + nrm * lift


def head_ref(c):
    return head_axis(clamp((c - BACK).dot(HF) / HL, 0, 1)) + HU * 0.05


JAW_V0 = 0.17


def jaw_prof(v):
    tip = 1 - 0.93 * smoothstep(0.92, 1.0, v)
    rear = 0.35 + 0.65 * math.sqrt(smoothstep(JAW_V0, JAW_V0 + 0.08, v))
    w, h, d = prof(v)
    wj = interp_(v, [(0.17, 0.44), (0.35, 0.37), (0.65, 0.27), (1.0, 0.13)]) * tip * rear
    dj = interp_(v, [(0.17, 0.36), (0.35, 0.27), (0.70, 0.17), (1.0, 0.08)]) * tip * rear
    top = -interp_(v, [(0, 0.34), (0.20, 0.24), (0.40, 0.15), (0.70, 0.11), (1.0, 0.07)]) - 0.012
    return wj, dj, top


def jaw_pt(a, v, lift=0.0):
    """下颚参数面：a=0 上沿（口腔面），a=π 下巴底。"""
    wj, dj, top = jaw_prof(v)
    c, sn = math.cos(a), math.sin(a)
    e = 2 / 2.8
    ax = head_axis(v)
    yc = top - dj * 0.5
    P = ax + HU * (yc + sgnpow(c, e) * dj * 0.5) + HS_ * (sgnpow(sn, e) * wj)
    C = ax + HU * yc
    nrm = P - C
    nrm = nrm.normalized() if nrm.length > 1e-6 else -HU
    return P + nrm * lift


def jaw_ref(c):
    v = clamp((c - BACK).dot(HF) / HL, JAW_V0, 1)
    wj, dj, top = jaw_prof(v)
    return head_axis(v) + HU * (top - dj * 0.5)


def armor_plate(ctx, M, name, surf, ref, a_rng, v_rng, lift, bone, depth=0.04, flare=0.0, flare_side=0.0,
                nu=10, nv=8, edge=0.016, seam=None):
    """贴合甲片 + 银色包边；seam 给定时在后缘外侧再加一道青色光缝。"""
    obj, loop_ = hull_patch(f"{ctx.title} {name}", surf, a_rng, v_rng, lift, depth, [M["armor"]], ref, nu, nv,
                            flare, flare_side)
    ctx.part(obj, rigid(bone))
    ctx.part(trim(f"{ctx.title} {name} rim", loop_ + [loop_[0]], edge, M["trim"], closed=True), rigid(bone))
    if seam:
        a0, a1 = a_rng(0.0)
        pts = [surf(lerp(a0, a1, t), v_rng[0] - 0.012, lift * 0.4) for t in [i / 12 for i in range(13)]]
        ctx.part(trim(f"{ctx.title} {name} seam", pts, seam, M["glow"]), rigid(bone))


def build_head(ctx, M):
    # 上颅底壳（深冰蓝钢）：甲片之间露出底层 + 光缝
    skull = surface(f"{ctx.title} skull", lambda uu, v: skull_pt(uu * TAU, v), 52, 32, [M["under"]], closed_u=True,
                    uvfn=lambda a, v: (a * 3, v * 2.5))
    orient(skull, head_ref)
    ctx.part(skull, rigid("Head"))
    # 吻部：左右各三段叠压甲（后缘外翘），段间青色光缝；中线一道深钢脊冠 + 发光脊线 + 鼻角冰晶
    for sd in (-1, 1):
        lab = "L" if sd < 0 else "R"
        for k, (v0, v1) in enumerate(((0.78, 0.975), (0.62, 0.80), (0.46, 0.64))):
            ah0, ah1 = 0.98 - 0.03 * k, 0.80 - 0.03 * k
            armor_plate(ctx, M, f"snout plate {lab}{k}", skull_pt, head_ref,
                        lambda vv, a=ah0, b=ah1, sd=sd: tuple(sorted((sd * 0.08, sd * lerp(a, b, vv)))),
                        (v0, v1), 0.022 + 0.012 * k, "Head", flare=0.035, seam=0.013, nu=8, nv=7)
    crest = [skull_pt(0.0, 0.40 + 0.56 * t, 0.03 + 0.03 * (1 - t)) for t in [i / 10 for i in range(11)]]
    ctx.part(sweep(f"{ctx.title} snout crest", crest, [0.05, 0.06, 0.06, 0.055, 0.05, 0.045, 0.04, 0.035, 0.03, 0.025,
                                                      0.015], [M["dark"]], n=10, per=2, fx=1.7, fy=0.45),
             rigid("Head"))
    ctx.part(trim(f"{ctx.title} snout crest glow", [p + HU * 0.07 for p in crest[1:-1]], 0.013, M["glow"], per=2),
             rigid("Head"))
    nb = skull_pt(0.0, 0.86, 0.02)
    ctx.part(crystals(f"{ctx.title} nose horn", [(nb - HU * 0.05, nb + (HU * 0.85 + HF * 0.5).normalized() * 0.38, 0.07, 6),
                                                 (nb - HF * 0.2, nb - HF * 0.2 + (HU * 0.9 + HF * 0.3).normalized() * 0.2,
                                                  0.045, 6)], [M["crystal"]], seed=17), rigid("Head"))
    # 额盾（中央）+ 眉甲（左右，压在眼缝上方）
    armor_plate(ctx, M, "forehead shield", skull_pt, head_ref, lambda vv: (-lerp(0.56, 0.44, vv), lerp(0.56, 0.44, vv)),
                (0.16, 0.45), 0.07, "Head", depth=0.05, flare=0.06, seam=0.016)
    for sd in (-1, 1):
        lab = "L" if sd < 0 else "R"
        rng_ = (lambda vv, sd=sd: tuple(sorted((sd * lerp(0.54, 0.60, vv), sd * lerp(1.06, 0.98, vv)))))
        armor_plate(ctx, M, f"brow plate {lab}", skull_pt, head_ref, rng_, (0.22, 0.48), 0.06, "Head", depth=0.05,
                    flare=0.07, flare_side=0.02)
        # 颊甲两层 + 上唇甲
        for q, (a0, a1, v0, v1, lf, fl) in enumerate(((1.52, 2.12, 0.05, 0.27, 0.055, 0.06),
                                                      (1.62, 2.05, 0.27, 0.50, 0.035, 0.03))):
            armor_plate(ctx, M, f"cheek plate {lab}{q}", skull_pt, head_ref,
                        lambda vv, a0=a0, a1=a1, sd=sd: tuple(sorted((sd * a0, sd * a1))), (v0, v1), lf, "Head",
                        flare=fl, seam=0.013 if q == 1 else None)
        armor_plate(ctx, M, f"upper lip {lab}", skull_pt, head_ref,
                    lambda vv, sd=sd: tuple(sorted((sd * 1.62, sd * lerp(2.28, 2.10, vv)))), (0.50, 0.975), 0.028,
                    "Head", depth=0.03, nu=6, nv=10)
        # 吻侧青色嵌线（吻甲与唇甲之间的深蓝底上）
        pts = [skull_pt(sd * 1.30, 0.53 + 0.42 * t, 0.012) for t in [i / 10 for i in range(11)]]
        ctx.part(trim(f"{ctx.title} snout inlay {lab}", pts, 0.016, M["glow"]), rigid("Head"))
        # 发光眼缝：细长斜缝（后端上挑、前端收尖）；眼窝一圈暗钢
        # sweep 截面：fx 为竖向、fy 为沿表面法向（外凸）；眼缝要凸出眼窝之外才看得见
        eye = [skull_pt(sd * (1.40 - 0.14 * t), 0.26 + 0.21 * t, 0.030) for t in [i / 8 for i in range(9)]]
        ctx.part(sweep(f"{ctx.title} eye slit {lab}", eye, [0.014, 0.045, 0.060, 0.064, 0.060, 0.050, 0.036, 0.018,
                                                             0.004], [M["core"]], n=8, per=2, fx=0.5, fy=0.5),
                 rigid("Head"))
        sock = [skull_pt(sd * (1.40 - 0.14 * t), 0.26 + 0.21 * t, 0.0) for t in [i / 8 for i in range(9)]]
        ctx.part(sweep(f"{ctx.title} eye socket {lab}", sock, [0.04, 0.085, 0.10, 0.105, 0.10, 0.085, 0.065, 0.04,
                                                               0.015], [M["dark"]], n=8, per=2, fx=0.75, fy=0.3),
                 rigid("Head"))
        # 鼻孔微光
        ctx.part(gem(f"{ctx.title} nostril {lab}", skull_pt(sd * 0.50, 0.95, 0.02), 0.035, M["glow"], (1, 1.8, 0.6)),
                 rigid("Head"))
        build_horns(ctx, M, sd, lab)
    # 口腔：上颚发光面 + 上排冰牙
    pal = surface(f"{ctx.title} palate", lambda uu, v: skull_pt(math.pi + (uu - 0.5) * 1.3, lerp(0.22, 0.95, v), 0.006),
                  8, 12, [M["maw"]], uvfn=lambda uu, v: (uu, v * 2.5))
    ctx.part(pal, rigid("Head"))
    teeth = []
    for k in range(8):
        v = 0.40 + k * 0.074
        for sd in (-1, 1):
            base = skull_pt(sd * 2.26, v, -0.01)
            Lt = 0.34 if k == 6 else (0.22 if k in (0, 1) else 0.17)
            teeth.append((base + HU * 0.05, base - HU * Lt + HF * 0.03 + HS_ * sd * 0.02, 0.042 if k == 6 else 0.032,
                          5))
    ctx.part(crystals(f"{ctx.title} upper fangs", teeth, [M["crystal"]], seed=11), rigid("Head"))
    build_jaw(ctx, M)
    build_crown(ctx, M)


def build_horns(ctx, M, sd, lab):
    """三层后掠头冠角：深冰蓝钢角身 + 银箍 + 顶面青色嵌线 + 刻面冰晶角尖。"""
    specs = (  # (a, v, 路径偏移列表 (后, 上, 外), 半径列表)
        (0.50, 0.22, [(0.35, 0.24, 0.10), (0.85, 0.46, 0.22), (1.40, 0.66, 0.30), (1.92, 0.90, 0.28)],
         [0.20, 0.16, 0.12, 0.075, 0.03]),
        (0.98, 0.14, [(0.35, 0.10, 0.20), (0.80, 0.22, 0.38), (1.25, 0.40, 0.48), (1.62, 0.64, 0.50)],
         [0.155, 0.125, 0.09, 0.055, 0.022]),
        (1.52, 0.10, [(0.30, -0.06, 0.20), (0.65, -0.04, 0.36), (1.00, 0.10, 0.44), (1.26, 0.28, 0.46)],
         [0.115, 0.095, 0.065, 0.038, 0.016]),
    )
    tips = []
    for q, (a, v, offs, rads) in enumerate(specs):
        b = skull_pt(sd * a, v, -0.05)
        pts = [b] + [b - HF * o[0] * HORN_BACK + HU * o[1] * HORN_UP + HS_ * sd * o[2] for o in offs]
        # 竖向略扁的刀形角身（fy 压窄横向）
        ctx.part(sweep(f"{ctx.title} horn {lab}{q}", pts, rads, [M["under"]], n=10, per=5, fy=0.72), rigid("Head"))
        path, rad = resample(pts, rads, per=6)
        m = len(path)
        for t in (0.22, 0.45, 0.66):
            i = int(t * (m - 1))
            T = (path[min(i + 1, m - 1)] - path[max(i - 1, 0)]).normalized()
            ring = [path[i] + (T.orthogonal().normalized() * math.cos(x) + T.cross(T.orthogonal().normalized()) *
                               math.sin(x)) * (rad[i] * 1.06 + 0.008) for x in [j / 14 * TAU for j in range(14)]]
            ctx.part(trim(f"{ctx.title} horn band {lab}{q}{t}", ring, 0.012 + rad[i] * 0.12, M["trim"], closed=True),
                     rigid("Head"))
        inl = []
        for i in range(1, int(0.82 * (m - 1))):
            T = (path[i + 1] - path[i - 1]).normalized()
            up = (HU - T * HU.dot(T)).normalized()
            inl.append(path[i] + up * rad[i] * 0.96)
        ctx.part(trim(f"{ctx.title} horn inlay {lab}{q}", inl, 0.010 + 0.004 * (2 - q), M["glow"]), rigid("Head"))
        d = (path[-1] - path[-3]).normalized()
        tips.append((path[-2], path[-1] + d * (0.34 - 0.07 * q), rads[-2] * 0.9, 6))
    ctx.part(crystals(f"{ctx.title} horn tips {lab}", tips, [M["crystal"]], seed=5 + sd), rigid("Head"))


def build_jaw(ctx, M):
    """下颚：深冰蓝钢颚骨 + 三段侧颌甲 + 下巴甲 + 下缘光缝 + 下排冰牙 + 发光舌面（挂 Jaw 骨）。"""
    jaw = surface(f"{ctx.title} jaw", lambda uu, v: jaw_pt(uu * TAU, lerp(JAW_V0, 1.0, v)), 36, 26, [M["under"]],
                  closed_u=True, uvfn=lambda a, v: (a * 2, v * 2))
    orient(jaw, jaw_ref)
    ctx.part(jaw, rigid("Jaw"))
    for sd in (-1, 1):
        lab = "L" if sd < 0 else "R"
        for k, (v0, v1) in enumerate(((0.22, 0.47), (0.44, 0.70), (0.67, 0.93))):
            armor_plate(ctx, M, f"jaw plate {lab}{k}", jaw_pt, jaw_ref,
                        lambda vv, sd=sd: tuple(sorted((sd * 0.95, sd * 2.45))), (v0, v1), 0.022 + 0.008 * (2 - k),
                        "Jaw", depth=0.035, flare=0.03, seam=0.012 if k > 0 else None)
    armor_plate(ctx, M, "chin plate", jaw_pt, jaw_ref, lambda vv: (2.35, TAU - 2.35), (0.78, 0.99), 0.03, "Jaw",
                depth=0.035, flare=0.03, nu=8, nv=6)
    pts = [jaw_pt(math.pi, lerp(0.24, 0.76, t), 0.012) for t in [i / 12 for i in range(13)]]
    ctx.part(trim(f"{ctx.title} jaw underglow", pts, 0.02, M["glow"]), rigid("Jaw"))
    tongue = surface(f"{ctx.title} tongue", lambda uu, v: jaw_pt((uu - 0.5) * 1.0, lerp(0.22, 0.92, v), 0.004), 8, 12,
                     [M["maw"]], uvfn=lambda uu, v: (uu, v * 2.5))
    ctx.part(tongue, rigid("Jaw"))
    teeth = []
    for k in range(7):
        v = 0.40 + k * 0.078
        for sd in (-1, 1):
            base = jaw_pt(sd * 0.85, v, -0.01)
            Lt = 0.22 if k == 5 else 0.12
            teeth.append((base - HU * 0.04, base + HU * Lt + HF * 0.03, 0.03, 5))
    ctx.part(crystals(f"{ctx.title} lower fangs", teeth, [M["crystal"]], seed=12), rigid("Jaw"))


CROWN = {}


def build_crown(ctx, M):
    """冰核王冠：后脑一簇玻璃质刻面冰晶（挂 Crown 骨，狂暴时放大）+ 银座 + 旋转银环（挂 CrownSpin 骨）。"""
    c = skull_pt(0.0, 0.17, -0.02)
    axis = (HU * 0.80 - HF * 0.60).normalized()
    pa = HS_
    pb = axis.cross(pa)
    CROWN.update(c=c, axis=axis)
    items = [(c - axis * 0.15, c + axis * 0.95, 0.18, 6)]
    for k in range(7):
        q = k / 7 * TAU + 0.3
        perp = pa * math.cos(q) + pb * math.sin(q)
        tilt = 0.50 if k % 2 == 0 else 0.72
        d = (axis * math.cos(tilt) + perp * math.sin(tilt)).normalized()
        L = 0.66 if k % 2 == 0 else 0.45
        items.append((c + perp * 0.10 - axis * 0.08, c + perp * 0.10 + d * L, 0.10 if k % 2 == 0 else 0.075, 6))
    ctx.attach(crystals(f"{ctx.title} crown crystals", items, [M["crystal"]], seed=3), "Crown")
    ctx.attach(blob(f"{ctx.title} crown heart", c + axis * 0.05, (0.13, 0.13, 0.13), [M["core"]], 14, 10), "Crown")
    # 银座：深蓝钢底盘 + 银箍 + 发光箍
    ctx.part(blob(f"{ctx.title} crown socket", c - axis * 0.02, (0.30, 0.30, 0.10), [M["dark"]], 20, 10,
                  frame=Matrix((pa, pb, axis)).transposed(), power=2.4), rigid("Head"))
    for q, (h, rr, rad, mat) in enumerate(((0.04, 0.31, 0.028, M["trim"]), (0.09, 0.24, 0.018, M["glow"]))):
        ring = [c + axis * h + (pa * math.cos(x) + pb * math.sin(x)) * rr for x in [j / 28 * TAU for j in range(28)]]
        ctx.part(trim(f"{ctx.title} crown socket ring {q}", ring, rad, mat, closed=True), rigid("Head"))
    # 旋转银环（网页端不驱动，由 CrownSpin 骨动画）
    hc = c + axis * 0.36
    HR = 0.68
    ring = [hc + (pa * math.cos(q) + pb * math.sin(q)) * HR for q in [i / 64 * TAU for i in range(64)]]
    objs = [trim(f"{ctx.title} crown halo", ring, 0.022, M["trim"], closed=True)]
    sh = []
    for k in range(12):
        q = k / 12 * TAU
        p = hc + (pa * math.cos(q) + pb * math.sin(q)) * HR
        o = (p - hc).normalized()
        L = 0.24 if k % 3 == 0 else 0.13
        sh.append((p - o * L * 0.45, p + o * L, 0.035 if k % 3 == 0 else 0.025, 6))
    objs.append(crystals(f"{ctx.title} crown halo shards", sh, [M["crystal"]], seed=8, double=True))
    for k in range(4):
        q = (k + 0.5) / 4 * TAU
        objs.append(gem(f"{ctx.title} halo gem {k}", hc + (pa * math.cos(q) + pb * math.sin(q)) * HR, 0.045,
                        M["core"], (1, 1, 1)))
    halo = join(objs, f"{ctx.ID}_CROWN", hc)
    ctx.attach(halo, "CrownSpin", keep=True)
    CROWN["hc"] = hc


def scale_head(ctx, n0p, n0a):
    """把 n0p / n0a 之后登记的头部件绕头根 HB 统一放大 HK 倍（部件先按 1 倍尺寸建）。"""
    S = Matrix.Translation(HB) @ Matrix.Scale(HK, 4) @ Matrix.Translation(-HB)
    for o in [o for o, _ in ctx.parts[n0p:]] + [o for o, *_ in ctx.attached[n0a:]]:
        loc = o.location.copy()
        o.data.transform(Matrix.Scale(HK, 4))
        o.data.update()
        o.location = S @ loc
    for key in ("c", "hc"):
        CROWN[key] = hk(CROWN[key])
    THROAT["tc"] = hk(THROAT["tc"])


# ===== 喉部冰核 =====
THROAT = {}


def build_throat_core(ctx, M):
    """口腔深处一枚冰核（Throat 骨，吐息时放大）：张颚时可见。"""
    # 放在口腔中段的咬合线上：闭口时被上下颌壳体包住，张口即露出
    tc = head_axis(0.33) - HU * 0.18
    THROAT["tc"] = tc
    ctx.attach(blob(f"{ctx.title} throat core", tc, (0.12, 0.12, 0.09), [M["core"]], 14, 10), "Throat")
    items = []
    for k in range(6):
        q = k / 6 * TAU
        d = (HF * 0.55 + (HS_ * math.cos(q) + HU * math.sin(q)) * 0.85).normalized()
        items.append((tc, tc + d * 0.20, 0.04, 6))
    ctx.attach(crystals(f"{ctx.title} throat shards", items, [M["crystal"]], seed=21), "Throat")


def build_gorget(ctx, M, sp):
    """颈前一枚护喉冰核（Gorget 骨，吐息 / 狂暴时放大）+ 银环铆钉座。"""
    s_ = sp.knot[CHEST + 3] - 0.25
    p, T, N, Bv, r = sp.at(s_)
    gc = p - N * (r * 1.02)
    THROAT["gc"], THROAT["gn"] = gc, -N
    ctx.attach(crystals(f"{ctx.title} gorget core", [(gc + N * 0.10, gc - N * 0.30, 0.16, 6)], [M["crystal"]],
                        seed=31, double=True), "Gorget")
    ctx.attach(blob(f"{ctx.title} gorget glow", gc, (0.12, 0.12, 0.12), [M["core"]], 12, 8), "Gorget")
    ring = [gc + (Bv * math.cos(q) + T * math.sin(q)) * 0.26 for q in [i / 32 * TAU for i in range(32)]]
    ctx.part(trim(f"{ctx.title} gorget ring", ring, 0.035, M["trim"], closed=True), rigid(sp.bone_at(s_)))
    items = []
    for k in range(8):
        q = k / 8 * TAU
        qp = gc + (Bv * math.cos(q) + T * math.sin(q)) * 0.34
        items.append((qp, -N, 0.035))
    ctx.part(studs(f"{ctx.title} gorget rivets", items, [M["trim"]], seg=6, rings=2), rigid(sp.bone_at(s_)))


# ===== 霜翼（第三轮：见 _b1r3_wing） =====
WING_B0 = {}


def wing_geo(side):
    return WingGeo(side, WING_B0.get(side))


def build_wings(ctx, M, sp):
    """两侧龙翼；翼膜内侧连到躯干侧面的 B0 点（取脊骨截面上靠后侧的一点，略沉入体内）。"""
    i = sp.idx(sp.knot[CHEST - 1])
    for side in (-1, 1):
        WING_B0[side] = section(sp, i, side * (1.57 - 0.40), groove=False) - sp.B[i] * side * 0.05
        build_wing(ctx, M, wing_geo(side))


# ===== 环绕冰棱 =====
ORBIT_C = Vector((0.0, -0.45, 3.2))


def build_orbit(ctx, M):
    items = []
    for k in range(14):
        a = k / 14 * TAU
        r = 3.05 + 0.15 * math.sin(k * 2.3)
        c = ORBIT_C + Vector((math.sin(a) * r, math.cos(a) * r, 0.25 * math.sin(k * 1.7)))
        d = Vector((math.cos(a), -math.sin(a), 0.25 * math.cos(k))).normalized()
        L = 0.60 if k % 2 == 0 else 0.38
        items.append((c - d * L * 0.5, c + d * L * 0.5, 0.10 if k % 2 == 0 else 0.07, 6))
    orbit = join([crystals(f"{ctx.title} orbit shards", items, [M["crystal"]], seed=90, double=True)],
                 f"{ctx.ID}_ORBIT", ORBIT_C)
    ctx.attach(orbit, "Orbit", keep=True)


def tris_report(ctx):
    """按材质 / 部件类统计三角面（控制游戏版预算）：环境变量 B1_TOP=N 额外列出最费面的 N 类部件。"""
    import os
    import re
    by, cat = {}, {}
    for o in [o for o, _ in ctx.parts] + [o for o, *_ in ctx.attached]:
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        m = o.data.materials[0].name if o.data.materials else "?"
        by[m] = by.get(m, 0) + n
        key = re.sub(r"[-+\d.]+| [LR]\b", "", o.name.replace(ctx.title, "")).strip()
        if os.environ.get("B1_MAT", "") in m:
            cat[key] = cat.get(key, 0) + n
    print(f"TRIS total {sum(by.values())}")
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
        print(f"    {v:7d}  {k}")
    for k, v in sorted(cat.items(), key=lambda kv: -kv[1])[:int(os.environ.get("B1_TOP", 0))]:
        print(f"      cat {v:7d}  {k}")


# ===== 构建 =====
def build(ctx):
    M = materials(ctx)
    sp = Spine()
    kw = KDWeights()
    bounds = sp.bounds()
    for i in range(len(sp.p)):
        w = interval_weights(sp.s[i], bounds, 0.24)
        for a in [q / 16 * TAU for q in range(16)]:
            kw.add(section(sp, i, a), w)
        kw.add(sp.p[i], w)
    kw.build()
    build_trunk(ctx, M, sp, kw)
    build_spines(ctx, M, sp)
    build_tail_blade(ctx, M, sp)
    n0p, n0a = len(ctx.parts), len(ctx.attached)
    build_head(ctx, M)
    build_throat_core(ctx, M)
    scale_head(ctx, n0p, n0a)
    build_gorget(ctx, M, sp)
    build_wings(ctx, M, sp)
    build_orbit(ctx, M)
    # 颈根 / 胸口银色项圈（带光环）
    for q, (s_, rs) in enumerate(((sp.knot[CHEST] + 0.25, 1.12), (sp.knot[CHEST + 2] + 0.1, 1.14))):
        p, T, N, Bv, r = sp.at(s_)
        for j, (dz, mat, rad) in enumerate(((0.0, M["trim"], 0.045), (0.09, M["glow"], 0.025))):
            ring = [p + T * dz + (N * math.cos(x) + Bv * math.sin(x) * 1.06) * r * (rs - 0.02 * j)
                    for x in [i / 44 * TAU for i in range(44)]]
            ctx.part(trim(f"{ctx.title} collar {q}{j}", ring, rad, mat, closed=True), fn(kw))
    # 颈侧腮缝：每侧三道青色光缝
    for sd in (-1, 1):
        for j in range(3):
            s0 = sp.knot[CHEST + 1] + 0.35 + j * 0.30
            pts = []
            for t in range(6):
                i = sp.idx(s0 + t * 0.06)
                pts.append(section(sp, i, sd * 1.75, groove=False) + sp.B[i] * sd * 0.01)
            ctx.part(trim(f"{ctx.title} gill {sd}{j}", pts, 0.022, M["glow"]), fn(kw))
    # 胸口冰核反应堆
    p, T, N, Bv, r = sp.at(sp.knot[CHEST] - 0.25)
    chest_c = p - N * r * 0.98
    ctx.part(blob(f"{ctx.title} chest core", chest_c, (0.22, 0.22, 0.22), [M["core"]], 18, 12), rigid("Core"))
    items = []
    for k in range(6):
        q = k / 6 * TAU
        dq = Bv * math.cos(q) + T * math.sin(q)
        items.append((chest_c + dq * 0.20, chest_c + dq * 0.52 - N * 0.10, 0.06, 6))
    ctx.part(crystals(f"{ctx.title} chest rays", items, [M["crystal"]], seed=70), rigid("Core"))
    for j, (rr, mat, rad) in enumerate(((0.34, M["trim"], 0.04),)):
        ring = [chest_c + (Bv * math.cos(q) + T * math.sin(q)) * rr + N * 0.03 * j for q in [i / 40 * TAU
                                                                                              for i in range(40)]]
        ctx.part(trim(f"{ctx.title} chest core ring {j}", ring, rad, mat, closed=True), rigid("Core"))
    bbox_report(ctx.id, [o for o, _ in ctx.parts] + [o for o, *_ in ctx.attached])
    tris_report(ctx)
    # 自检：非相邻脊段之间的最小距离（盘绕不应贴得过近）
    worst = (9.0, 0, 0)
    for i in range(0, len(sp.p), 4):
        for j in range(i + 80, len(sp.p), 4):
            d = (sp.p[i] - sp.p[j]).length - sp.r[i] - sp.r[j]
            if d < worst[0]:
                worst = (d, sp.s[i], sp.s[j])
    print(f"SPINE CLEARANCE min gap {worst[0]:.2f} m between s={worst[1]:.1f} and s={worst[2]:.1f} (length {sp.L:.1f} m)")
    return {"sp": sp}


# ===== 骨骼 =====
def skeleton(rig, st):
    sp = st["sp"]
    rig.bone("Root", (0, 0, 0), (0, 0, 0.5))
    rig.bone("Hover", (0, 0, 0.5), (0, 0, 1.2), "Root")
    rig.translate["Hover"] = "_hover"
    k = [Vector(c) for c in CTRL]
    C = k[CHEST]

    def roll_at(p):
        i = min(range(len(sp.p)), key=lambda q: (sp.p[q] - p).length)
        return sp.N[i]
    rig.bone("Core", C, k[CHEST + 1], "Hover", roll=roll_at(C))
    prev = "Hover"
    for j, name in enumerate(BODY):
        a, b = k[CHEST - j], k[CHEST - j - 1]
        rig.bone(name, a, b, prev, roll=roll_at(a.lerp(b, 0.5)))
        prev = name
    prev = "Core"
    for j, name in enumerate(NECK):
        a, b = k[CHEST + 1 + j], k[CHEST + 2 + j]
        rig.bone(name, a, b, prev, roll=roll_at(a.lerp(b, 0.5)))
        prev = name
    rig.bone("Head", HB, HB + HF * 1.6 * HK, "Neck3", roll=HU)
    hinge = hk(head_axis(JAW_V0 + 0.02) - HU * 0.25)
    rig.bone("Jaw", hinge, hk(head_axis(0.97) - HU * 0.12), "Head", roll=HU)
    mouth = hk(head_axis(1.0) - HU * 0.10)
    rig.bone("Breath", mouth, mouth + HF * 0.6, "Head", roll=HU)          # 吐息特效挂点（无几何）
    tc = THROAT["tc"]
    rig.bone("Throat", tc, tc + HF * 0.3, "Head", roll=HU)
    gc, gn = THROAT["gc"], THROAT["gn"]
    rig.bone("Gorget", gc, gc + gn * 0.3, "Neck3", roll=Z)
    c = CROWN["c"]
    rig.bone("Crown", c, c + CROWN["axis"] * 0.4, "Head", roll=HF)
    rig.bone("CrownSpin", CROWN["hc"], CROWN["hc"] + CROWN["axis"] * 0.4, "Head", roll=HF)
    rig.bone("Orbit", ORBIT_C, ORBIT_C + Vector((0, 0, 0.6)), "Hover", roll=Y)
    for side, label in ((-1, "L"), (1, "R")):
        g = wing_geo(side)
        rig.bone(f"WingA.{label}", g.S, g.E, "Core", roll=Z)
        rig.bone(f"WingB.{label}", g.E, g.W, f"WingA.{label}", roll=Z)
        for q, (d, L) in enumerate(g.F):
            rig.bone(f"WingF{q}.{label}", g.W, g.W + d * L, f"WingB.{label}", roll=Z)
    register_chains(rig, "Spine", 1, len(BODY))
    rig.scaled = ["Crown", "Throat", "Gorget"]


# ===== 动作 =====
def dorsal(rig, st, name):
    """骨的静止背向轴（armature 空间）。"""
    sp = st["sp"]
    h, t = rig.SEG[name]
    m = h.lerp(t, 0.5)
    i = min(range(0, len(sp.p), 3), key=lambda q: (sp.p[q] - m).length)
    return sp.N[i], (t - h).normalized()


def body_wave(rig, st, p, t, amp=0.10, vamp=0.04, phase=0.75, k=1, coil=0.0, lift=0.0):
    """沿脊骨的行波：绕各节背向轴侧摆（蛇形）+ 绕侧向轴起伏；coil 让盘身整体收紧。"""
    for j, name in enumerate(BODY):
        n, d = st["axes"][name]
        lat = d.cross(n).normalized()
        taper = 0.55 + 0.45 * j / (len(BODY) - 1)
        # 收紧只作用在水平盘圈段（胸下竖直段的“背向轴”朝后，绕它转会把整圈甩到地下）
        yaw = amp * taper * math.sin(k * t - j * phase) + coil * smoothstep(1.5, 4.0, j)
        pitch = vamp * math.sin(k * t - j * phase + 1.2) + lift * (1 - j / len(BODY))
        p[name] = R((n, yaw), (lat, pitch))


def neck_pose(rig, st, p, pitch=(0.0, 0.0, 0.0), yaw=(0.0, 0.0, 0.0), head=0.0, head_yaw=0.0):
    """pitch 正为后仰；head 正为抬头。"""
    for name, pt, yw in zip(NECK, pitch, yaw):
        n, d = st["axes"][name]
        lat = d.cross(n).normalized()
        p[name] = R((lat, pt), (Z, yw))
    p["Head"] = R((HS_, head), (Z, head_yaw))


def jaw_open(p, a):
    """下颚张开 a 弧度（绕头部侧轴向下转）。"""
    p["Jaw"] = R((HS_, -a))


def wings_pose(rig, st, p, wlift=0.0, wsweep=0.0, close=0.0, elbow=0.0, wrist=0.0, twist=0.0):
    """翼姿态（静止几何 = 完全展开）：
    wlift 肩上抬（正为上扬，绕前后轴）；wsweep 肩前兜（正为向前，绕竖轴）；twist 肱骨旋前（正为前缘抬高）；
    elbow 肘弯（正为前臂折回肱骨）；close 指骨收拢量（0 全展、1 并成一束，各指绕翼面法向向 F0 并拢）；
    wrist 整把指骨在翼面内的后掠量（正为向后张得更开）。"""
    for side, label in ((-1, "L"), (1, "R")):
        g = st["wg"][side]
        nw, ang, ax = st["wax"][side]
        ah = (g.E - g.S).normalized()
        p[f"WingA.{label}"] = R((ah, side * twist), (Y, -side * wlift), (Z, side * wsweep))
        p[f"WingB.{label}"] = R((ax, elbow))
        for q in range(5):
            p[f"WingF{q}.{label}"] = R((nw, -close * ang[q] + wrist * (0.4 + 0.15 * q)))


def idle_pose(rig, st, t):
    p = {}
    p["_hover"] = 0.14 * math.sin(t)
    p["Core"] = R((X, 0.03 * math.sin(t + 0.6)))
    body_wave(rig, st, p, t, amp=0.035, vamp=0.02, phase=0.6)
    neck_pose(rig, st, p, pitch=(0.03 * math.sin(t + 0.8), 0.03 * math.sin(t + 1.2), 0.02 * math.sin(t + 1.6)),
              yaw=(0.04 * math.sin(t), 0.03 * math.sin(t + 0.4), 0.0), head=0.05 * math.sin(t + 2.0),
              head_yaw=0.08 * math.sin(t + 0.3))
    wings_pose(rig, st, p, wlift=0.12 + 0.12 * math.sin(t), wsweep=0.05 + 0.04 * math.sin(t + 0.5),
               close=0.12 + 0.06 * math.sin(t - 0.8), elbow=0.22 + 0.09 * math.sin(t - 0.4),
               wrist=0.04 * math.sin(t + 1.0))
    jaw_open(p, 0.05 + 0.03 * math.sin(2 * t))
    p["_scale"] = {"Crown": 1.0 + 0.04 * math.sin(2 * t), "Throat": 0.85 + 0.05 * math.sin(2 * t),
                   "Gorget": 1.0 + 0.05 * math.sin(2 * t + 1.0)}
    p["CrownSpin"] = R((CROWN["axis"], t))
    p["Orbit"] = R((Z, -t))
    return p


def move_pose(rig, st, t):
    """游动：一个循环 3 个蜿蜒周期、3 次振翼（循环 96 帧，让环绕冰棱与王冠银环慢转一整圈）。"""
    p = {}
    w = 3 * t
    p["_hover"] = 0.10 * math.sin(2 * w) + 0.2
    p["Core"] = R((X, -0.10 + 0.04 * math.sin(2 * w)), (Z, 0.06 * math.sin(w)))
    body_wave(rig, st, p, t, amp=0.16, vamp=0.05, phase=0.8, k=3)
    neck_pose(rig, st, p, pitch=(-0.08, 0.02 * math.sin(2 * w), 0.10), yaw=(-0.08 * math.sin(w), -0.05 * math.sin(w),
                                                                          -0.02 * math.sin(w)),
              head=0.06 + 0.03 * math.sin(2 * w + 1), head_yaw=-0.04 * math.sin(w))
    # 振翼：上扬时肘弯、指骨略收（上冲），下拍时肘伸直、翼面全开并后掠（下压）
    wings_pose(rig, st, p, wlift=0.20 + 0.28 * math.sin(w), wsweep=0.14 - 0.10 * math.sin(w),
               close=0.18 + 0.16 * math.cos(w + 0.3), elbow=0.22 + 0.26 * math.cos(w + 0.2),
               wrist=0.10 * math.cos(w + 0.8), twist=0.10 * math.sin(w + 1.0))
    jaw_open(p, 0.07)
    p["_scale"] = {"Crown": 1.0, "Throat": 0.9, "Gorget": 1.0 + 0.04 * math.sin(2 * w)}
    p["CrownSpin"] = R((CROWN["axis"], t))
    p["Orbit"] = R((Z, -t))
    return p


def pose_from(rig, st, q, t):
    p = {}
    p["_hover"] = q["hover"]
    p["Core"] = R((X, q["rear"]), (Z, q["twist"]))
    body_wave(rig, st, p, t * 0.8, amp=q["wave"], vamp=0.03, phase=0.8, coil=q["coil"], lift=q["lift"])
    neck_pose(rig, st, p, pitch=(q["n1"], q["n2"], q["n3"]), yaw=(q["yaw"] * 0.4, q["yaw"] * 0.3, q["yaw"] * 0.3),
              head=q["head"], head_yaw=q["hyaw"])
    wings_pose(rig, st, p, wlift=q["wlift"], wsweep=q["wsweep"], close=q["close"], elbow=q["elbow"], wrist=q["wrist"],
               twist=q["wtwist"])
    jaw_open(p, q["jaw"])
    p["_scale"] = {"Crown": q["crown"], "Throat": q["throat"], "Gorget": q["gorget"]}
    p["CrownSpin"] = R((CROWN["axis"], q["halo"]))
    p["Orbit"] = R((Z, -q["orbit"]))
    return p


BASE = {"hover": 0.0, "rear": 0.0, "twist": 0.0, "wave": 0.035, "coil": 0.0, "lift": 0.0, "n1": 0.0, "n2": 0.0,
        "n3": 0.0, "yaw": 0.0, "head": 0.0, "hyaw": 0.0, "wlift": 0.12, "wsweep": 0.05, "close": 0.12, "elbow": 0.22,
        "wrist": 0.0, "wtwist": 0.0,
        "jaw": 0.05, "crown": 1.0, "throat": 0.85, "gorget": 1.0, "halo": 0.0, "orbit": 0.0}


def attack_keys():
    """吐息姿态：1 → 9 昂首后仰蓄气（喉核胀亮）、双翼向前包拢（肘弯、指骨并拢，像披风裹住胸颈）
    → 13 头颈前探、下颚大张，双翼猛然向后展开到极限 → 13–24 保持吐息并左右扫（翼面全展微颤）→ 27 收颚 → 31 收势。
    吐息光束由游戏特效挂在 Breath 骨上。"""
    rear = {"hover": 0.35, "rear": 0.30, "n1": 0.28, "n2": 0.22, "n3": 0.10, "head": 0.28, "wlift": 0.20, "wsweep": 0.60,
            "close": 0.75, "elbow": 0.35, "wrist": -0.05, "wtwist": 0.10, "jaw": 0.30, "crown": 1.12, "throat": 1.45,
            "gorget": 1.35, "halo": 1.5, "orbit": 0.3, "lift": 0.06}
    # 前探：下颈前压、上颈与头回抬，头朝前下方约 25°（吐向地面前方）；双翼向后甩开
    lunge = {"hover": 0.10, "rear": -0.20, "n1": -0.30, "n2": 0.03, "n3": 0.12, "head": 0.26, "wlift": 0.36,
             "wsweep": -0.10, "close": -0.04, "elbow": -0.06, "wrist": 0.10, "wtwist": -0.05, "jaw": 0.62,
             "crown": 1.22, "throat": 1.9, "gorget": 1.6, "halo": 3.0, "orbit": 0.7, "yaw": 0.22, "hyaw": 0.10}
    sweep_r = dict(lunge, yaw=-0.22, hyaw=-0.10, halo=6.0, orbit=1.2, throat=2.0, jaw=0.66, wlift=0.34, wrist=0.14)
    fade = dict(lunge, yaw=0.0, hyaw=0.0, jaw=0.30, throat=1.2, gorget=1.2, halo=7.5, orbit=1.5, rear=-0.05,
                n1=-0.10, n2=0.0, n3=0.03, head=0.02, wlift=0.28, wsweep=0.06, close=0.18, elbow=0.18, wrist=0.0)
    end = dict(BASE, halo=TAU * 1.5, orbit=TAU / 7 * 2)
    return with_defaults(BASE, [(1, {}, "io"), (9, rear, "io"), (13, lunge, "in"), (16, dict(lunge, throat=2.0, wlift=0.40), "out"),
                                (23, sweep_r, "io"), (27, fade, "io"), (31, end, "io")])


def enrage_keys():
    """狂暴：1 → 12 盘身收紧、双翼向前裹拢、低头蓄力 → 20 双翼怒张到极限（高举、微后掠、翼面绷开）、
    昂首咆哮、王冠爆开 → 20–36 震颤 → 49 收势。"""
    tight = {"hover": 0.05, "coil": 0.10, "lift": 0.0, "n1": -0.12, "n2": -0.20, "n3": -0.05, "head": -0.20,
             "wlift": 0.12, "wsweep": 0.55, "close": 0.80, "elbow": 0.32, "wrist": 0.0, "wtwist": 0.08, "crown": 0.9,
             "throat": 1.1, "gorget": 1.2, "halo": 1.0, "orbit": 0.6, "wave": 0.02}
    roar = {"hover": 0.55, "coil": 0.14, "lift": 0.05, "rear": 0.14, "n1": 0.15, "n2": 0.12, "n3": 0.10,
            "head": 0.22, "wlift": 0.30, "wsweep": 0.10, "close": -0.10, "elbow": -0.10, "wrist": 0.18, "wtwist": -0.12,
            "jaw": 0.66, "crown": 1.55, "throat": 1.7, "gorget": 1.6, "halo": 4.0, "orbit": 2.0, "wave": 0.02}
    roar2 = dict(roar, halo=9.0, orbit=3.6, head=0.27, crown=1.6, wlift=0.34, throat=1.85)
    settle = dict(BASE, halo=4 * TAU - 0.3, orbit=TAU - 0.1, crown=1.05)
    end = dict(BASE, halo=4 * TAU, orbit=TAU)
    return with_defaults(BASE, [(1, {}, "io"), (12, tight, "io"), (20, roar, "back"), (28, roar2, "out"),
                                (36, dict(roar2, halo=15.0, orbit=4.6), "lin"), (44, settle, "io"), (49, end, "io")])


def animate(rig, st):
    st["axes"] = {name: dorsal(rig, st, name) for name in BODY + NECK}
    st["wg"] = {side: wing_geo(side) for side in (-1, 1)}
    st["wax"] = {side: wing_axes(st["wg"][side]) for side in (-1, 1)}
    loop(rig, "Idle", 96, lambda t: idle_pose(rig, st, t), step=2)
    loop(rig, "Move", 96, lambda t: move_pose(rig, st, t), step=1)
    ak = attack_keys()
    sampled(rig, "Attack", 30, lambda f: pose_from(rig, st, track(ak, f), f * 0.25))
    ek = enrage_keys()

    def enrage(f):
        q = track(ek, f)
        amp = smoothstep(19, 22, f) * (1 - smoothstep(34, 40, f))
        q["n3"] += 0.04 * math.sin(f * 2.3) * amp
        q["hyaw"] += 0.05 * math.sin(f * 1.9) * amp
        q["wlift"] += 0.06 * math.sin(f * 2.7) * amp
        return pose_from(rig, st, q, f * 0.25)
    sampled(rig, "Enrage", 48, enrage)
    ground_check(rig, CLIPS, BODY + ["Head", "Jaw"], "body bone")
    seam_check(rig, ("Idle", "Move"))
