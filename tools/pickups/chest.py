"""圣物匣（剑匣）· 哥特式小圣物匣，三个顶层命名节点：CHEST_BODY / CHEST_LID / CHEST_HALO。

坐标（Blender，Z 向上；导出后 glTF Y 向上）：宽沿 X（±0.50）、深沿 Y（±0.32）、正面朝 -Y（= glTF +Z，游戏相机一侧）。
  CHEST_BODY  原点在底面中心：底座 + 匣身 + 四角立柱 + 尖拱嵌板 + 宝石 + 发光嵌线 + 铰链座。
  CHEST_LID   节点原点放在后侧铰链轴上（Blender y=+0.28、z=0.40；导出后 glTF z=-0.28、y=0.40），铰链轴沿 X。
              尖拱山墙盖：屋脊沿 X，山墙面在 ±X，四角尖顶、脊上一排小尖饰、前面带锁扣宝石。
              开盖 = CHEST_LID 绕 X 轴旋转 -110°（three.js 的 rotation.x = -110° = -1.9199 rad；负号 = 前沿向上翻起）。
  CHEST_HALO  原点在光环中心（匣身正上方 z=1.02），光环平面水平（法线 +Y），网页端让它绕 Y 自转。
材质（共 4 个）：Chest Brass 黄铜主体 / Chest Iron 暗金结构 / Chest Inlay 发光嵌线 / Chest Gem Glow 宝石与光环内圈。
发光（金 = 超频）：嵌线 #ffd291 ×1.0（名含 inlay，游戏里 ×1.4 = 1.4）、宝石与光环内圈 #ffc65c ×1.2（名含 glow，游戏里 ×1.2 = 1.44）。
"""

import math

from mathutils import Vector

from .geo import Mesh, make_material
from .recipes import Part

BRASS, IRON, INLAY, GLOW = 0, 1, 2, 3

# ---- 尺寸 ----
X0, Y0 = 0.44, 0.265            # 匣身半宽 / 半深
ZB0, ZB1 = 0.095, 0.40          # 匣身下沿 / 上沿（盖子底面）
HINGE = (0.0, 0.28, 0.40)       # 铰链轴（Blender 坐标）
LID_X = 0.45                    # 盖子半宽
LID_S = 0.56                    # 盖子深（后沿 → 前沿）
LID_WALL = 0.05                 # 盖子四周的直墙高度
LID_B0, LID_B1 = math.radians(70), math.radians(36)     # 屋面曲线切线倾角：起拱处 70°（陡）→ 屋脊处 36°（两坡夹角 108° = 尖拱的“尖”）
US = (0.0, 1 / 3, 2 / 3, 1.0)   # 屋面曲线采样（0 = 起拱点、1 = 屋脊）
HALO_Z = 1.02


def materials():
    brass = make_material("Chest Brass", "#e0b04a", metal=0.55, rough=0.42)
    iron = make_material("Chest Iron", "#5a4422", metal=0.5, rough=0.5)
    inlay = make_material("Chest Inlay", "#6b5428", metal=0.2, rough=0.5, emit="#ffd291", strength=1.0)
    glow = make_material("Chest Gem Glow", "#d4a23a", metal=0.0, rough=0.2, spec=0.5, emit="#ffc65c", strength=1.2)
    return [brass, iron, inlay, glow]


# ===== 通用小件 =====
def gem(m, origin, normal, r, h, sides=6, rot=0.0, mat=GLOW, bezel=False, two_tier=False):
    """贴面宝石：腰线环 → 冠部 → 台面（朝外凸出 h）；bezel=True 加一圈暗金底托。"""
    with m.frame(origin, normal):
        ref = m.pt((0, 0, -h))
        girdle = m.vs(Mesh.ngon(r, sides, 0.0, rot))
        if two_tier:
            crown = m.vs(Mesh.ngon(r * 0.78, sides, h * 0.55, rot + math.pi / sides))
            table = m.vs(Mesh.ngon(r * 0.42, sides, h, rot))
            m.loft([girdle, crown, table], mat, ref=ref)
        else:
            table = m.vs(Mesh.ngon(r * 0.52, sides, h, rot))
            m.loft([girdle, table], mat, ref=ref)
        m.cap(table, mat, ref)
        if bezel:
            m.lathe([(r * 1.32, -0.002), (r * 1.32, h * 0.42), (r * 1.02, h * 0.62)], sides, IRON,
                    rot=rot, cap_bottom=False, cap_top=False)


def pad(m, origin, normal, r=0.011, mat=INLAY):
    """电路线末端的小六边形焊盘（贴面）。"""
    with m.frame(origin, normal):
        ring = m.vs(Mesh.ngon(r, 6, 0.004))
        m.cap(ring, mat, m.pt((0, 0, -0.05)))


def lancet_path(cx, z0, a, hs, ratio=1.3):
    """尖拱轮廓（二维 x-z）：左下 → 起拱点 → 弧 → 拱尖 → 右侧对称 → 右下；返回 (点列, 拱尖高度)。"""
    R = ratio * a
    cos_t = 1 - a / R
    phi_t = math.acos(cos_t)
    zs = z0 + hs
    left = [(cx - a, z0), (cx - a, zs)]
    for phi in (phi_t * 0.52,):
        left.append((cx + (R - a) - R * math.cos(phi), zs + R * math.sin(phi)))
    apex = (cx, zs + R * math.sin(phi_t))
    right = [(2 * cx - x, z) for x, z in reversed(left)]
    return left + [apex] + right, apex[1]


def arch_panel(m, to3d, normal, cx, z0, a, hs, gem_r, gem_h, gem_z, big=False):
    """一块尖拱嵌板：暗色底板 + 黄铜凸边 + 中央宝石。to3d(u, z) 把面内二维坐标映射到 3D 点。"""
    pts2, _ = lancet_path(cx, z0, a, hs)
    n = Vector(normal)
    inner, _ = lancet_path(cx, z0 + 0.012, a - 0.014, hs)                # 底板：比外框缩进
    ids = m.vs([Vector(to3d(u, z)) + n * 0.003 for u, z in inner])
    m.cap(ids, IRON, m.pt(Vector(to3d(cx, z0 + hs)) - n * 0.05))
    path = [to3d(u, z) for u, z in pts2]
    m.rib(BRASS, path, [normal] * len(path), 0.013, 0.014, inset=None)
    gem(m, Vector(to3d(cx, gem_z)) + n * 0.003, normal, gem_r, gem_h, sides=8 if big else 6,
        rot=math.pi / 8 if big else 0.0, bezel=big, two_tier=big)


def line(m, to3d, normal, pts2, half_w=0.0045, lift=0.003, mat=INLAY, end_pad=True):
    """面内二维折线 → 贴面发光线（带末端焊盘）。"""
    path = [to3d(u, z) for u, z in pts2]
    m.ribbon(mat, path, [normal] * len(path), half_w, lift)
    if end_pad:
        pad(m, Vector(path[-1]) + Vector(normal) * lift, normal)


# =====================================================================
# 匣身
# =====================================================================
def build_body():
    m = Mesh()
    rect = lambda hx, hy, z: [(-hx, -hy, z), (hx, -hy, z), (hx, hy, z), (-hx, hy, z)]
    # 底座下层（暗金）：三环收口，顶面小台
    r0, r1, r2 = (m.vs(rect(*k)) for k in ((0.50, 0.32, 0.0), (0.50, 0.32, 0.035), (0.475, 0.30, 0.06)))
    m.loft([r0, r1, r2], IRON)
    m.cap(r2, IRON, m.pt((0, 0, 0.02)))
    # 底座上层（黄铜）
    s0, s1, s2 = (m.vs(rect(*k)) for k in ((0.462, 0.282, 0.06), (0.462, 0.282, 0.082), (0.452, 0.272, 0.095)))
    m.loft([s0, s1, s2], BRASS)
    m.cap(s2, BRASS, m.pt((0, 0, 0.07)))
    # 匣身主体 + 顶面：黄铜外框，内里一块发光面（开盖时才看得到：光从匣里透出来）
    b0, b1 = m.vs(rect(X0, Y0, ZB0)), m.vs(rect(X0, Y0, ZB1))
    m.loft([b0, b1], BRASS)
    inner = m.vs(rect(X0 - 0.05, Y0 - 0.05, ZB1 - 0.004))
    m.loft([b1, m.vs(rect(X0 - 0.05, Y0 - 0.05, ZB1))], BRASS, ref=m.pt((0, 0, ZB1 - 0.1)))
    m.cap(inner, INLAY, m.pt((0, 0, ZB1 - 0.1)))
    # 四角立柱（六棱，柱头柱脚外张）
    for sx in (-1, 1):
        for sy in (-1, 1):
            with m.place((sx * X0, sy * Y0, 0.0)):
                m.lathe([(0.040, ZB0), (0.032, ZB0 + 0.022), (0.032, ZB1 - 0.024), (0.042, ZB1)], 6, IRON,
                        rot=math.pi / 6, cap_bottom=False, cap_top=False)
    # 前面三块尖拱嵌板（中央大、两侧小）
    front = lambda u, z: (u, -Y0, z)
    nF = (0, -1, 0)
    arch_panel(m, front, nF, 0.0, 0.14, 0.115, 0.07, 0.054, 0.034, 0.238, big=True)
    for sx in (-1, 1):
        arch_panel(m, front, nF, sx * 0.30, 0.14, 0.065, 0.06, 0.030, 0.022, 0.218)
    # 两个侧面：一块尖拱嵌板
    for sx in (-1, 1):
        side = (lambda s: lambda u, z: (s * X0, u, z))(sx)
        arch_panel(m, side, (sx, 0, 0), 0.0, 0.14, 0.10, 0.07, 0.044, 0.028, 0.226)
    # 发光电路线：嵌板之间的折线 + 底座前沿的灯带 + 侧面折线
    for sx in (-1, 1):
        line(m, front, nF, [(sx * 0.125, 0.205), (sx * 0.175, 0.205), (sx * 0.175, 0.262), (sx * 0.215, 0.262)])
        line(m, front, nF, [(sx * 0.125, 0.168), (sx * 0.165, 0.168), (sx * 0.165, 0.118), (sx * 0.38, 0.118)])
        m.ribbon(INLAY, [(sx * 0.14, -0.282, 0.071), (sx * 0.40, -0.282, 0.071)], [(0, -1, 0)] * 2, 0.0045, 0.003)
        side = (lambda s: lambda u, z: (s * X0, u, z))(sx)
        for sy in (-1, 1):
            line(m, side, (sx, 0, 0), [(sy * 0.125, 0.19), (sy * 0.175, 0.19), (sy * 0.175, 0.145), (sy * 0.225, 0.145)])
    # 铰链座（后沿，两侧各一节，轴沿 X）
    for sx in (-1, 1):
        with m.frame((sx * 0.30, HINGE[1], HINGE[2]), (1, 0, 0)):
            m.lathe([(0.024, -0.07), (0.024, 0.07)], 5, IRON, cap_bottom=False, cap_top=False)
    return Part("CHEST_BODY", m, None, (0, 0, 0))


# =====================================================================
# 盖子（局部坐标：原点在铰链轴上；y_local = -d，d 为离后沿的距离；z_local 向上）
# =====================================================================
def _roof_curve(n=400):
    """屋面曲线：切线倾角 β 沿弧长线性地从 70° 降到 36°（先陡后缓 = 尖拱轮廓），积分得 (d, 高)，水平总长缩放到半跨。"""
    xs, zs, bs = [0.0], [0.0], [LID_B0]
    for i in range(1, n + 1):
        t = i / n
        bm = LID_B0 + (LID_B1 - LID_B0) * (t - 0.5 / n)
        xs.append(xs[-1] + math.cos(bm) / n)
        zs.append(zs[-1] + math.sin(bm) / n)
        bs.append(LID_B0 + (LID_B1 - LID_B0) * t)
    k = (LID_S / 2) / xs[-1]
    return [x * k for x in xs], [z * k for z in zs], bs


_CURVE = _roof_curve()
LID_RISE = LID_WALL + _CURVE[1][-1]        # 屋脊高度（盖子局部坐标）


def arc_pt(side, u):
    """屋面曲线上 u ∈ [0,1] 处的点 (y, z) 与外法线 (ny, nz)。side=0 后坡（靠铰链）、1 前坡。"""
    xs, zs, bs = _CURVE
    f = u * (len(xs) - 1)
    i = min(int(f), len(xs) - 2)
    t = f - i
    d = xs[i] + (xs[i + 1] - xs[i]) * t
    h = LID_WALL + zs[i] + (zs[i + 1] - zs[i]) * t
    beta = bs[i] + (bs[i + 1] - bs[i]) * t
    if side == 0:
        return (-d, h), (math.sin(beta), math.cos(beta))
    return (-(LID_S - d), h), (-math.sin(beta), math.cos(beta))


def profile():
    """剖面轮廓（后沿底 → 后坡 → 屋脊 → 前坡 → 前沿底），返回 [(y, z, ny, nz)]。"""
    pts = [(0.0, 0.0, 1.0, 0.0)]
    for u in US:
        (y, z), (ny, nz) = arc_pt(0, u)
        pts.append((y, z, ny, nz))
    for u in reversed(US[:-1]):
        (y, z), (ny, nz) = arc_pt(1, u)
        pts.append((y, z, ny, nz))
    pts.append((-LID_S, 0.0, -1.0, 0.0))
    return pts


def roof_path(side, x_u):
    """曲面上的折线：[(x, u), ...] → 3D 点列与外法线；沿弧的线段按 Δu ≤ 0.2 细分，免得弦线埋进曲面。"""
    pts, nrm = [], []

    def add(x, a):
        (y, z), (ny, nz) = arc_pt(side, a)
        pts.append((x, y, z))
        nrm.append((0, ny, nz))

    add(*x_u[0])
    for (px, pa), (x, a) in zip(x_u, x_u[1:]):
        if x == px and a != pa:
            steps = max(1, math.ceil(abs(a - pa) / 0.2))
            for i in range(1, steps):
                add(x, pa + (a - pa) * i / steps)
        add(x, a)
    return pts, nrm


def build_lid():
    m = Mesh()
    prof = profile()
    ridge = len(US)          # 剖面点序列里屋脊点的下标（第 0 点是后沿底）
    n_back = ridge + 1
    # ---- 屋面：前后两个壳（脊线处不共用顶点 → 脊线是硬边，弧面内平滑）----
    rings_back = [m.vs([(sx * LID_X, y, z) for (y, z, _, _) in prof[:n_back]]) for sx in (-1, 1)]
    rings_front = [m.vs([(sx * LID_X, y, z) for (y, z, _, _) in prof[ridge:]]) for sx in (-1, 1)]
    ref = m.pt((0, -LID_S / 2, 0.12))
    m.loft(rings_back, BRASS, closed=False, smooth=True, ref=ref)
    m.loft(rings_front, BRASS, closed=False, smooth=True, ref=ref)
    # ---- 山墙面（±X）：暗色底板 + 黄铜尖拱凸边 + 宝石 ----
    for sx in (-1, 1):
        end = m.vs([(sx * LID_X, y, z) for (y, z, _, _) in prof])
        m.cap(end, BRASS, ref)
        inset = [(sx * (LID_X + 0.003), y - ny * 0.034 - (0.0 if z > 0.012 else 0.0), max(z - nz * 0.034, 0.03)) for (y, z, ny, nz) in prof]
        ids = m.vs(inset)
        m.cap(ids, IRON, ref)
        path = [(sx * (LID_X + 0.003), y - ny * 0.030, max(z - nz * 0.030, 0.026)) for (y, z, ny, nz) in prof]
        m.rib(BRASS, path, [(sx, 0, 0)] * len(path), 0.012, 0.013, inset=None)
        gem(m, (sx * (LID_X + 0.003), -LID_S / 2, 0.16), (sx, 0, 0), 0.034, 0.024)
    # ---- 底面（开盖后可见的内侧）：暗色底板 + 发光框线 ----
    bot = m.vs([(-LID_X, 0, 0), (LID_X, 0, 0), (LID_X, -LID_S, 0), (-LID_X, -LID_S, 0)])
    m.cap(bot, IRON, m.pt((0, -LID_S / 2, 0.2)))
    for (p, q) in (((-0.36, -0.08), (0.36, -0.08)), ((-0.36, -0.48), (0.36, -0.48)),
                   ((-0.36, -0.08), (-0.36, -0.48)), ((0.36, -0.08), (0.36, -0.48))):
        m.ribbon(INLAY, [(p[0], p[1], -0.003), (q[0], q[1], -0.003)], [(0, 0, -1)] * 2, 0.007, 0.0)
    # ---- 屋面肋：x=±0.30 两道暗金拱肋，x=0 一条黄铜扣带（只走前坡，下接锁扣）----
    for sx in (-0.30, 0.30):
        path = [(sx, y, z) for (y, z, _, _) in prof]
        m.rib(IRON, path, [(0, ny, nz) for (_, _, ny, nz) in prof], 0.024, 0.016, inset=None)
    strap = prof[ridge:]
    m.rib(BRASS, [(0.0, y, z) for (y, z, _, _) in strap], [(0, ny, nz) for (_, _, ny, nz) in strap], 0.034, 0.011, inset=0.7)
    # ---- 前坡锁扣：暗金底板 + 宝石 ----
    (yl, zl), (nyl, nzl) = arc_pt(1, 0.12)
    n_lock = Vector((0, nyl, nzl)).normalized()
    with m.frame((0.0, yl, zl), n_lock):
        m.box(IRON, (0, 0, 0.004), (0.10, 0.12, 0.012), bottom=False)
    gem(m, Vector((0.0, yl, zl)) + n_lock * 0.010, n_lock, 0.036, 0.026, sides=8, rot=math.pi / 8, bezel=True, two_tier=True)
    # ---- 屋面发光电路线（前后坡、左右对称）----
    for side in (0, 1):
        for sx in (-1, 1):
            pts, nrm = roof_path(side, [(sx * 0.06, 0.40), (sx * 0.20, 0.40), (sx * 0.20, 0.78), (sx * 0.265, 0.78)])
            m.ribbon(INLAY, pts, nrm, 0.0045, 0.004)
            pad(m, Vector(pts[-1]) + Vector(nrm[-1]) * 0.004, nrm[-1])
    # ---- 脊上小尖饰（四棱锥）+ 两端大尖饰 ----
    (yr, zr), _ = arc_pt(0, 1.0)
    for i in range(-3, 4):
        base = [(i * 0.135 + 0.020 * math.cos(math.pi / 4 + k * math.pi / 2),
                 yr + 0.020 * math.sin(math.pi / 4 + k * math.pi / 2), zr - 0.004) for k in range(4)]
        m.pyramid(BRASS, base, (i * 0.135, yr, zr + 0.052))
    for sx in (-1, 1):
        with m.place((sx * (LID_X + 0.012), yr, zr - 0.004)):
            m.lathe([(0.034, 0.0), (0.027, 0.022), (0.0, 0.098)], 4, BRASS, rot=math.pi / 4, cap_bottom=False)
    # ---- 四角尖顶（与匣身立柱同轴）----
    for sx in (-1, 1):
        for y in (Y0 - HINGE[1], -(HINGE[1] + Y0)):        # y_local：后角 = Y0 - 0.28，前角 = -0.28 - Y0
            with m.place((sx * X0, y, 0.0)):
                m.lathe([(0.040, 0.0), (0.031, 0.17), (0.040, 0.182), (0.0, 0.30)], 4, IRON,
                        rot=math.pi / 4, cap_bottom=False)
    # ---- 铰链节（盖子的两节，与匣身的两节交错）----
    for sx in (-1, 1):
        with m.frame((sx * 0.12, 0.0, 0.0), (1, 0, 0)):
            m.lathe([(0.024, -0.07), (0.024, 0.07)], 5, IRON, cap_bottom=False, cap_top=False)
    return Part("CHEST_LID", m, None, HINGE)


# =====================================================================
# 光环（局部坐标：原点在环心，环面在 XY、法线 +Z → glTF +Y）
# =====================================================================
def build_halo():
    m = Mesh()
    N = 18
    R, hw, hh = 0.255, 0.019, 0.012
    # 黄铜外环：菱形截面扁条
    rings = []
    for i in range(N):
        a = math.tau * i / N
        c, s = math.cos(a), math.sin(a)
        rings.append(m.vs([((R - hw) * c, (R - hw) * s, 0.0), (R * c, R * s, hh), ((R + hw) * c, (R + hw) * s, 0.0), (R * c, R * s, -hh)]))
    rings.append(rings[0])
    m.loft(rings, BRASS)
    # 发光内圈：贴在黄铜环内沿的扁环（上下两面）
    for z, sgn in ((0.003, 1), (-0.003, -1)):
        o = m.vs([((R - hw) * math.cos(math.tau * i / N), (R - hw) * math.sin(math.tau * i / N), z) for i in range(N)])
        n = m.vs([(0.19 * math.cos(math.tau * i / N), 0.19 * math.sin(math.tau * i / N), z) for i in range(N)])
        for i in range(N):
            j = (i + 1) % N
            m.face(GLOW, [o[i], o[j], n[j], n[i]], (0, 0, -sgn))
    # 外沿放射尖：长短不一（光环自转时看得出转动）
    lens = [0.105, 0.045, 0.075, 0.045, 0.09, 0.045, 0.06, 0.045]
    for i, ln in enumerate(lens):
        a = math.tau * i / len(lens) + 0.12
        with m.frame((0, 0, 0), (math.cos(a), math.sin(a), 0), x_hint=(0, 0, 1)):
            # 局部 Z = 径向向外；底面在 R+hw 处
            base = [(0.007, 0.0, R + hw - 0.004), (0.0, 0.016, R + hw - 0.004), (-0.007, 0.0, R + hw - 0.004), (0.0, -0.016, R + hw - 0.004)]
            m.pyramid(BRASS, base, (0, 0, R + hw + ln))
    # 四颗发光小菱晶（嵌在环上，按 90° 分布）
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        with m.place((R * c, R * s, hh + 0.004)):
            ring = m.vs([(0.020 * math.cos(t * math.pi / 2), 0.020 * math.sin(t * math.pi / 2), 0.0) for t in range(4)])
            top, bot = m.v((0, 0, 0.028)), m.v((0, 0, -0.012))
            m.fan(ring, top, GLOW, ref=m.pt((0, 0, -0.005)))
            m.fan(ring, bot, GLOW, ref=m.pt((0, 0, 0.005)))
    return Part("CHEST_HALO", m, None, (0, 0, HALO_Z))


def build_chest():
    mats = materials()
    parts = [build_body(), build_lid(), build_halo()]
    return [Part(p.name, p.mesh, mats, p.loc) for p in parts]
