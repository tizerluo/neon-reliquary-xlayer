"""NYX 的几何建模：躯干、面甲、兜帽、轻甲、手、布料、光环与针刃。

坐标：Blender Z 向上，角色正面朝 +Y（与骑士资产一致），单位米；悬浮高度已计入。
每个部件登记到 PARTS，附带蒙皮权重规格，供 build_nyx.py 绑定骨骼。
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from nyx_lib import (TAU, VIOLET, apply_all, attach_texture, bm_object, circuit_cloth_maps,
                     clamp, ellipsoid, image_from_array, interp, lerp, material, smoothstep,
                     solidify, subsurf, surface, tabard_maps, tube)


def crest(x):
    """|sin|^0.6：圆润外凸的褶峰 + 收紧的内凹褶谷，取值 [-1, 1]。"""
    return abs(math.sin(x)) ** 0.6 * 2 - 1


def cloth_fold(a, v, freq, amp, seed):
    phase = 0.9 * math.sin(a * 2.3 + seed) + 0.5 * math.sin(a * 3.7 + seed * 1.7)
    phase2 = 0.7 * math.sin(a * 1.9 + seed * 2.1)
    mod = 0.65 + 0.35 * math.sin(a * 3.1 + seed * 0.7 + v * 1.3)
    return amp * mod * (0.72 * crest(a * freq + phase) + 0.28 * v * crest(a * freq * 2.1 + phase2))

PARTS = []          # (对象, 权重规格)
HANDS = {}          # 手部标架与手指关节，供骨骼使用
ARMS = {}           # 肩、肘、腕位置


def part(obj, spec):
    PARTS.append((obj, spec))
    return obj


def orient(obj, ref):
    """若多数面法线朝向参考点/轴，则整体翻转，保证法线朝外。"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    score = 0.0
    for f in bm.faces:
        c = f.calc_center_median()
        score += f.normal.dot(c - ref(c)) * f.calc_area()
    if score < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()


def axis_ref(c):
    return Vector((0, 0, c.z))


def transform_obj(obj, matrix):
    obj.data.transform(matrix)
    obj.data.update()


# ===== 材质 =====
def make_materials():
    m = {
        "bodysuit": material("Nyx bodysuit weave", (0.018, 0.013, 0.026), 0.05, 0.62, sheen=0.12,
                             sheen_tint=(0.5, 0.4, 0.8)),
        "obsidian": material("Nyx obsidian lacquer", (0.012, 0.009, 0.017), 0.55, 0.23, coat=1.0,
                             coat_rough=0.05),
        "gauntlet": material("Nyx gauntlet alloy", (0.030, 0.026, 0.038), 0.85, 0.30, coat=0.4),
        "platinum": material("Nyx platinum trim", (0.80, 0.78, 0.86), 1.0, 0.22),
        "cloth": material("Nyx void velvet", (0.02, 0.014, 0.03), 0.0, 0.80, sheen=0.08,
                          sheen_tint=(0.40, 0.30, 0.62), spec=0.28),
        "tabard": material("Nyx tabard circuitry", (0.02, 0.014, 0.03), 0.0, 0.66, sheen=0.08,
                           sheen_tint=(0.40, 0.30, 0.62), spec=0.3),
        "hem": material("Nyx hem light", (0.25, 0.14, 0.5), 0.0, 0.4, emit=VIOLET, strength=4.5),
        "lining": material("Nyx violet lining", (0.06, 0.014, 0.11), 0.0, 0.5, sheen=0.35,
                           sheen_tint=(0.8, 0.5, 1.0)),
        "void": material("Nyx hood void", (0.002, 0.0015, 0.004), 0.0, 0.95, emit=(0.30, 0.16, 0.62),
                         strength=0.05),
        "mask": material("Nyx black glass mask", (0.006, 0.006, 0.010), 0.1, 0.07, coat=1.0,
                         coat_rough=0.02, spec=0.8),
        "glow": material("Nyx violet core glow", (0.5, 0.3, 0.9), 0.0, 0.3, emit=VIOLET, strength=8.0),
        "inlay": material("Nyx violet circuit inlay", (0.3, 0.18, 0.55), 0.0, 0.35, emit=VIOLET,
                          strength=3.2),
        "halo": material("Nyx halo dark steel", (0.05, 0.045, 0.06), 0.9, 0.28, coat=0.5),
        "needle": material("Nyx needle crystal core", (0.035, 0.016, 0.07), 0.7, 0.18, coat=1.0),
    }
    for key, maps, strength in (("cloth", circuit_cloth_maps(), 3.0), ("tabard", tabard_maps(), 3.4)):
        base, emission, normal = maps
        mat = m[key]
        attach_texture(mat, image_from_array(f"Nyx {key} base", base), "Base Color")
        attach_texture(mat, image_from_array(f"Nyx {key} circuits", emission), "Emission Color")
        mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = strength
        attach_texture(mat, image_from_array(f"Nyx {key} normal", normal, True), "Normal", 0.6)
    return m


# ===== 躯干 =====
TORSO = [(1.12, (0.150, 0.118, -0.005)), (1.20, (0.152, 0.118, -0.004)),
         (1.28, (0.140, 0.108, 0.000)), (1.36, (0.118, 0.088, 0.004)),
         (1.43, (0.116, 0.087, 0.006)), (1.50, (0.126, 0.090, 0.006)),
         (1.57, (0.136, 0.094, 0.006)), (1.63, (0.142, 0.096, 0.004)),
         (1.69, (0.148, 0.092, 0.000)), (1.735, (0.150, 0.086, -0.004)),
         (1.765, (0.128, 0.076, -0.006)), (1.79, (0.075, 0.062, -0.004)),
         (1.805, (0.052, 0.050, 0.000))]


def torso_point(a, z, grow=0.0):
    """a=0 为正前方（+Y），顺时针（俯视）增大；grow 为沿截面外扩量。"""
    rx, ry, yo = interp(TORSO, z)
    x = (rx + grow) * math.sin(a)
    front = max(0.0, math.cos(a))
    bust = 0.024 * (math.exp(-((x - 0.068) ** 2) / 0.0011) + math.exp(-((x + 0.068) ** 2) / 0.0011))
    bust *= front ** 2 * math.exp(-((z - 1.612) ** 2) / 0.0016)
    blade = 0.008 * max(0.0, -math.cos(a)) ** 2 * math.exp(-((z - 1.66) ** 2) / 0.004)
    return Vector((x, yo + (ry + grow) * math.cos(a) + bust - blade, z))


def front_angle(x, z, grow):
    rx = interp(TORSO, z)[0] + grow
    return math.asin(clamp(x / rx, -0.999, 0.999))


def build_torso(M):
    body = surface("Nyx torso", lambda u, v: torso_point(u * TAU, lerp(1.805, 1.12, v)), 40, 30,
                   [M["bodysuit"]], closed_u=True)
    orient(body, axis_ref)
    subsurf(body, 1)
    part(apply_all(body), ("invdist", ["Pelvis", "Spine", "Chest", "Neck"]))
    neck = tube("Nyx neck", [(0, 0, 1.79), (0, 0.006, 1.86), (0, 0.012, 1.925)],
                [0.050, 0.042, 0.040], [M["bodysuit"]], n=16)
    part(neck, ("invdist", ["Chest", "Neck", "Head"]))
    head = ellipsoid("Nyx head void", (0, 0.010, 1.968), (0.074, 0.086, 0.098), [M["void"]])
    part(head, ("rigid", {"Head": 1.0}))


# ===== 面甲 =====
MASK_C = Vector((0, 0.046, 1.965))


def mask_point(x, z):
    """面甲前表面的解析近似（用于贴合光缝与刻线）。"""
    lx, lz = x / 0.070, (z - MASK_C.z) / 0.098
    if lz < 0:
        k = (-lz) ** 1.4
        lx = lx / max(0.2, 1 - 0.62 * k)
    r2 = lx * lx + lz * lz
    y = math.sqrt(max(0.0, 1 - min(r2, 1.0))) * 0.055
    if lz < 0:
        y += 0.18 * ((-lz) ** 1.4) * y
    return Vector((x, MASK_C.y + y, z))


def front_projector(obj):
    """沿 -Y 方向把 (x, z) 投射到网格前表面，返回贴面点（可沿法线抬起）。"""
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())

    def project(x, z, lift=0.0):
        loc, nrm, _, _ = bvh.ray_cast(Vector((x, 1.0, z)), Vector((0, -1, 0)))
        return loc + nrm * lift if loc else mask_point(x, z)
    return project


def build_mask(M):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.02], context="VERTS")
    for v in bm.verts:
        x, y, z = v.co
        if z < 0:                                  # 下颌拉长并收成 V 形尖端
            z *= 1.22
            k = (-z) ** 1.35
            x *= max(0.08, 1 - 0.66 * k)
            y += 0.16 * k * max(0.0, y)
        if z > 0.45:
            z = 0.45 + (z - 0.45) * 0.55             # 压低额顶穹面
        x *= 1 - 0.07 * (1 - abs(z))               # 颧面收平
        front = max(0.0, y)
        prow = 0.10 * math.exp(-(x / 0.18) ** 2) * front            # 鼻梁中脊
        brow = 0.06 * math.exp(-((z - 0.26) / 0.08) ** 2) * front   # 眉弓
        groove = -0.035 * math.exp(-((z - 0.12) / 0.035) ** 2) * front * (1 - smoothstep(0.5, 0.75, abs(x)))
        v.co = Vector((x * 0.068, (y + prow + brow + groove) * 0.055, z * 0.096)) + MASK_C
    mask = bm_object("Nyx mask", bm, [M["mask"]])
    orient(mask, lambda c: Vector((0, 0.0, 1.965)))
    solidify(mask, 0.004, -1)
    subsurf(mask, 1)
    apply_all(mask)
    part(mask, ("rigid", {"Head": 1.0}))
    project = front_projector(mask)
    # 眉下光缝：向中心下压的 V 形，嵌在凹槽里，读作锐利的目光
    slit = [project(x, 1.9745 + 0.011 * abs(x) / 0.044 + 0.003 * (x / 0.044) ** 4, 0.0012)
            for x in [i / 16 * 0.088 - 0.044 for i in range(17)]]
    part(tube("Nyx visor slit", slit, [0.0022] * len(slit), [M["glow"]], n=8, fx=0.65, fy=1.0,
              up=(0, 0, 1)), ("rigid", {"Head": 1.0}))
    # 竖向刻线只走光缝以下的鼻梁中脊，避免与光缝交成准星
    line = [project(0, z, 0.0010) for z in [1.962 - i * 0.0085 for i in range(12)]]
    part(tube("Nyx mask meridian", line, [0.0010] * len(line), [M["inlay"]], n=6),
         ("rigid", {"Head": 1.0}))
    gem = ellipsoid("Nyx mask gem", project(0, 2.010, 0.003), (0.0042, 0.0026, 0.0075), [M["glow"]], 12, 8)
    part(gem, ("rigid", {"Head": 1.0}))
    # 护喉：两层甲片护住颈部，前端略低
    for k, (z0, z1, r0, r1) in enumerate(((1.782, 1.832, 0.084, 0.066), (1.822, 1.872, 0.068, 0.052))):
        def gorget(u, v, z0=z0, z1=z1, r0=r0, r1=r1):
            a = u * TAU
            z = lerp(z0, z1, v) - 0.018 * max(0.0, math.cos(a)) ** 4 * (1 - v)
            r = lerp(r0, r1, v)
            return Vector((r * math.sin(a), 0.004 + 0.006 * v + r * math.cos(a) * 0.92, z))
        g = surface(f"Nyx gorget {k}", gorget, 48, 6, [M["obsidian"]], closed_u=True)
        orient(g, axis_ref)
        solidify(g, 0.004, 1)
        subsurf(g, 1)
        part(apply_all(g), ("invdist", ["Chest", "Neck"]))
        rim = [gorget(i / 48, 1.0) for i in range(48)]
        rim = [p + Vector((p.x, p.y - 0.004, 0)).normalized() * 0.005 for p in rim]
        part(tube(f"Nyx gorget {k} trim", rim, [0.0022] * 48, [M["platinum"]], n=6, closed=True, per=1),
             ("invdist", ["Chest", "Neck"]))


# ===== 兜帽 =====
HOOD_R = [(0, 0.014), (0.1, 0.080), (0.28, 0.124), (0.48, 0.137), (0.66, 0.146), (0.82, 0.165),
          (1.0, 0.200)]
HOOD_Y = [(0, -0.080), (0.2, -0.035), (0.4, 0.012), (0.55, 0.022), (0.72, 0.008), (1.0, -0.030)]
HOOD_OPEN = [(0, 0.30), (0.12, 0.56), (0.28, 0.86), (0.5, 0.92), (0.66, 0.84), (0.76, 0.52),
             (0.86, 0.30), (1.0, 0.34)]
HOOD_SY = [(0, 1.05), (0.25, 1.25), (0.6, 1.28), (0.8, 1.05), (1.0, 0.92)]


def hood_point(u, v):
    z = lerp(2.215, 1.745, v)
    r, yo, op = interp(HOOD_R, v), interp(HOOD_Y, v), interp(HOOD_OPEN, v)
    a = op + u * (TAU - 2 * op)
    fold = 0.009 * crest(a * 5 + 0.5) * smoothstep(0.35, 1.0, v)
    seam = -0.006 * math.exp(-((a - math.pi) / 0.08) ** 2) * (1 - v)
    roll = 0.012 * math.exp(-min(u, 1 - u) / 0.03)
    rr = r + fold + seam + roll
    return Vector((rr * math.sin(a), yo + rr * math.cos(a) * interp(HOOD_SY, v), z))


def build_hood(M):
    hood = surface("Nyx hood", hood_point, 84, 52, [M["cloth"], M["void"], M["platinum"]],
                   uvfn=lambda u, v: (u, 0.72 + 0.28 * (1 - v)))
    orient(hood, lambda c: Vector((0, -0.02, c.z)))
    solidify(hood, 0.011, -1, inner_offset=1, rim_offset=2)
    part(apply_all(hood), ("hood",))
    seam = []
    for i in range(40):
        p = hood_point(0.5, 0.03 + i * 0.024)
        seam.append(p + (p - Vector((0, -0.02, p.z))).normalized() * 0.0025)
    part(tube("Nyx hood seam", seam, [0.0022] * 40, [M["platinum"]], n=6, per=1), ("hood",))


# ===== 胸甲、腹甲、胸核与嵌线 =====
def cuirass_point(u, v):
    a = u * TAU
    front = max(0.0, math.cos(a))
    zt = 1.778 + 0.016 * (1 - math.cos(a)) / 2 - 0.055 * front ** 8
    zb = 1.425 - 0.045 * front ** 6
    return torso_point(a, lerp(zt, zb, v), 0.010)


def build_armor(M):
    cuirass = surface("Nyx cuirass", cuirass_point, 80, 28, [M["obsidian"]], closed_u=True)
    orient(cuirass, axis_ref)
    solidify(cuirass, 0.008, 1)
    subsurf(cuirass, 1)
    part(apply_all(cuirass), ("invdist", ["Spine", "Chest"]))
    for v, name in ((0, "neckline"), (1, "underline")):
        pts = [cuirass_point(i / 96, v) for i in range(96)]
        pts = [p + Vector((p.x, p.y, 0)).normalized() * 0.010 for p in pts]
        part(tube(f"Nyx cuirass {name} trim", pts, [0.0034] * len(pts), [M["platinum"]], n=8,
                  closed=True, per=1), ("invdist", ["Spine", "Chest"]))
    # 胸前龙骨脊线
    keel = [torso_point(0, z, 0.0205) for z in [1.395 + i * 0.0165 for i in range(20)]]
    part(tube("Nyx cuirass keel", keel, [0.0040] * len(keel), [M["platinum"]], n=8),
         ("invdist", ["Spine", "Chest"]))
    # 腹甲两层，前端收尖
    for k, (zt, zb, grow) in enumerate(((1.432, 1.378, 0.024), (1.388, 1.330, 0.030))):
        def fauld(u, v, zt=zt, zb=zb, grow=grow):
            a = u * TAU
            z = lerp(zt, zb - 0.030 * max(0.0, math.cos(a)) ** 4, v)
            return torso_point(a, z, grow + v * 0.010)
        f = surface(f"Nyx fauld {k}", fauld, 64, 8, [M["obsidian"]], closed_u=True)
        orient(f, axis_ref)
        solidify(f, 0.006, 1)
        subsurf(f, 1)
        part(apply_all(f), ("invdist", ["Pelvis", "Spine"]))
        edge = [fauld(i / 80, 1.0) for i in range(80)]
        edge = [p + Vector((p.x, p.y, 0)).normalized() * 0.007 for p in edge]
        part(tube(f"Nyx fauld {k} trim", edge, [0.0027] * len(edge), [M["platinum"]], n=6,
                  closed=True, per=1), ("invdist", ["Pelvis", "Spine"]))
    # 胸前电路嵌线：左右镜像，沿胸甲外表面
    half = [
        [(0.012, 1.622), (0.034, 1.646), (0.034, 1.700), (0.058, 1.724), (0.104, 1.726)],
        [(0.014, 1.604), (0.046, 1.574), (0.086, 1.574), (0.112, 1.548)],
        [(0.007, 1.585), (0.007, 1.502), (0.030, 1.478), (0.030, 1.442)],
        [(0.046, 1.574), (0.046, 1.522), (0.070, 1.498), (0.100, 1.498)],
    ]
    for side in (-1, 1):
        for i, path in enumerate(half):
            pts = []
            for (x0, z0), (x1, z1) in zip(path, path[1:]):
                for s in range(8):
                    t = s / 8
                    x, z = lerp(x0, x1, t) * side, lerp(z0, z1, t)
                    pts.append(torso_point(front_angle(x, z, 0.0195), z, 0.0195))
            x, z = path[-1][0] * side, path[-1][1]
            end = torso_point(front_angle(x, z, 0.0195), z, 0.0195)
            pts.append(end)
            part(tube(f"Nyx chest circuit {side} {i}", pts, [0.0019] * len(pts), [M["inlay"]], n=6,
                      per=1), ("invdist", ["Spine", "Chest"]))
            part(ellipsoid(f"Nyx chest via {side} {i}", end, (0.0045,) * 3, [M["glow"]], 12, 8),
                 ("invdist", ["Spine", "Chest"]))
    # 四芒星胸核 + 铂金星框 + 圆环
    center = torso_point(0, 1.615, 0.020)

    def star(name, scale, depth, mat, dy):
        tips = [(0, 0.058), (0.030, 0), (0, -0.075), (-0.030, 0)]
        bm = bmesh.new()
        ring = []
        for i, (tx, tz) in enumerate(tips):
            ring.append(bm.verts.new((tx * scale, 0, tz * scale)))
            a = math.pi / 4 + i * math.pi / 2
            ring.append(bm.verts.new((math.sin(a) * 0.011 * scale, 0, math.cos(a) * 0.011 * scale)))
        face = bm.faces.new(ring)
        ext = bmesh.ops.extrude_face_region(bm, geom=[face])
        for v in [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]:
            v.co.y += depth
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        obj = bm_object(name, bm, [mat])
        transform_obj(obj, Matrix.Translation(center + Vector((0, dy, 0))))
        return obj

    part(star("Nyx star core", 1.0, 0.009, M["glow"], 0.004), ("rigid", {"Chest": 1.0}))
    part(star("Nyx star frame", 1.32, 0.006, M["platinum"], 0.0), ("rigid", {"Chest": 1.0}))
    ring = [center + Vector((math.sin(t) * 0.030, -0.001, math.cos(t) * 0.030))
            for t in [i / 40 * TAU for i in range(40)]]
    part(tube("Nyx star ring", ring, [0.0026] * 40, [M["platinum"]], n=6, closed=True, per=1),
         ("rigid", {"Chest": 1.0}))


# ===== 肩甲 =====
def lame_point(side, k, s, t):
    shoulder = Vector((side * 0.168, -0.004, 1.748))
    th0, th1 = ((0.08, 0.92), (0.70, 1.30), (1.10, 1.66))[k]
    radius = (0.112, 0.107, 0.101)[k]
    phi = s * 1.32
    taper = 1 - abs(s) ** 2.6
    mid, half = (th0 + th1) / 2, (th1 - th0) / 2
    th = mid + (t - 0.5) * 2 * half * taper
    d = Vector((math.cos(phi) * math.sin(th) * side, math.sin(phi) * math.sin(th) * 1.18, math.cos(th)))
    p = shoulder + d * radius * (1 + 0.06 * (1 - abs(s)))
    if k == 0:
        spire = 0.11 * math.exp(-((s + 0.30) / 0.20) ** 2) * (1 - t) ** 2.0
        p += Vector((side * 0.28, -0.22, 1.0)).normalized() * spire
    return shoulder + Matrix.Rotation(side * 0.30, 3, "Y") @ (p - shoulder)


def build_pauldrons(M):
    for side, label in ((-1, "L"), (1, "R")):
        shoulder = Vector((side * 0.168, -0.004, 1.748))
        for k in range(3):
            lame = surface(f"Nyx pauldron {label}{k}", lambda u, v, k=k, side=side:
                           lame_point(side, k, 2 * u - 1, v), 30, 9, [M["obsidian"]])
            orient(lame, lambda c, s=shoulder: s)
            solidify(lame, 0.007, 0)
            subsurf(lame, 1)
            part(apply_all(lame), ("rigid", {"Chest": 0.35, f"UpperArm.{label}": 0.65}))
            edge = [lame_point(side, k, 2 * i / 48 - 1, 1.0) for i in range(49)]
            edge = [p + (p - shoulder).normalized() * 0.004 for p in edge]
            part(tube(f"Nyx pauldron {label}{k} trim", edge, [0.0026] * len(edge), [M["platinum"]], n=6,
                      per=1), ("rigid", {"Chest": 0.35, f"UpperArm.{label}": 0.65}))
        gem = lame_point(side, 0, 0.25, 0.55)
        gem += (gem - shoulder).normalized() * 0.006
        part(ellipsoid(f"Nyx pauldron gem {label}", gem, (0.0075,) * 3, [M["glow"]], 12, 8),
             ("rigid", {"Chest": 0.35, f"UpperArm.{label}": 0.65}))


# ===== 手臂、护臂与手 =====
def build_arms(M):
    for side, label in ((-1, "L"), (1, "R")):
        inner = Vector((side * 0.10, -0.002, 1.735))
        shoulder = Vector((side * 0.168, -0.004, 1.742))
        elbow = Vector((side * 0.300, 0.055, 1.515))
        wrist = Vector((side * 0.440, 0.160, 1.350))
        ARMS[label] = {"shoulder": shoulder, "elbow": elbow, "wrist": wrist}
        mid = (shoulder + elbow) / 2
        arm = tube(f"Nyx arm {label}", [inner, shoulder, mid, elbow, wrist],
                   [0.042, 0.046, 0.040, 0.033, 0.026], [M["bodysuit"]], n=16)
        part(arm, ("chain", [f"UpperArm.{label}", f"Forearm.{label}", f"Hand.{label}"], "Chest", 0.05))
        # 上臂甲：外侧半包覆甲片 + 下缘铂金边
        axis = (elbow - shoulder).normalized()
        o = Vector((side, 0, 0.6))
        o = (o - axis * o.dot(axis)).normalized()
        w2 = axis.cross(o)

        def rere(u, v, o=o, w2=w2, shoulder=shoulder, elbow=elbow):
            th = (2 * u - 1) * 1.75
            c = shoulder.lerp(elbow, lerp(0.22, 0.86, v))
            r = lerp(0.059, 0.049, v) + 0.005 * math.sin(v * math.pi)
            return c + (o * math.cos(th) + w2 * math.sin(th)) * r

        def on_axis(c, s=shoulder, e=elbow):
            return s + (e - s) * clamp((c - s).dot(e - s) / (e - s).length_squared)

        plate = surface(f"Nyx rerebrace {label}", rere, 24, 10, [M["obsidian"]])
        orient(plate, on_axis)
        solidify(plate, 0.004, 1)
        subsurf(plate, 1)
        part(apply_all(plate), ("rigid", {f"UpperArm.{label}": 1.0}))
        rim = [rere(i / 24, 1.0) for i in range(25)]
        rim = [p + (p - on_axis(p)).normalized() * 0.005 for p in rim]
        part(tube(f"Nyx rerebrace trim {label}", rim, [0.0022] * 25, [M["platinum"]], n=6, per=1),
             ("rigid", {f"UpperArm.{label}": 1.0}))
        # 前臂垂幔：沿前臂下侧垂下的尖角布片
        down = Vector((side * 0.18, -0.12, -1)).normalized()

        def drape(u, v, elbow=elbow, wrist=wrist, down=down, side=side):
            anchor = elbow.lerp(wrist, 0.08 + 0.55 * u) + Vector((0, -0.012, -0.03))
            length = lerp(0.44, 0.15, u ** 0.8)
            ripple = 0.012 * math.sin(u * 9 + v * 3) * v
            return anchor + down * (v * length) + Vector((side * ripple, ripple * 0.5, 0))

        sheet = surface(f"Nyx sleeve drape {label}", drape, 14, 20, [M["cloth"], M["lining"]],
                        uvfn=lambda u, v: (0.05 + u * 0.25, 1 - v))
        orient(sheet, lambda c: Vector((0, 0, c.z)))
        solidify(sheet, 0.005, 0, inner_offset=1)
        part(apply_all(sheet), ("rigid", {f"Forearm.{label}": 1.0}))
        edge = [drape(i / 30, 1.0) for i in range(31)]
        part(tube(f"Nyx sleeve hem {label}", edge, [0.0022] * 31, [M["hem"]], n=6, per=1),
             ("rigid", {f"Forearm.{label}": 1.0}))
        # 护臂：开口锥管 + 肘部尖刺 + 两端铂金环 + 外侧发光线
        fdir = (wrist - elbow).normalized()
        a0, a1 = elbow + fdir * 0.03, wrist - fdir * 0.012
        guard = tube(f"Nyx vambrace {label}", [a0, (a0 + a1) / 2, a1 - fdir * 0.02, a1],
                     [0.042, 0.039, 0.041, 0.047], [M["obsidian"]], n=20, cap=False)   # 腕口外扩
        solidify(guard, 0.004, 1)
        subsurf(guard, 1)
        part(apply_all(guard), ("rigid", {f"Forearm.{label}": 1.0}))
        out = Vector((side, -0.35, 0.25)).normalized()
        out = (out - fdir * out.dot(fdir)).normalized()
        part(tube(f"Nyx elbow spur {label}", [elbow + out * 0.02 - fdir * 0.005,
                                               elbow + out * 0.055 - fdir * 0.045],
                  [0.016, 0.0], [M["obsidian"]], n=8, per=1), ("rigid", {f"Forearm.{label}": 1.0}))
        for c, r in ((a0, 0.043), (a1, 0.048)):
            n1 = out
            n2 = fdir.cross(n1)
            ring = [c + (n1 * math.cos(t) + n2 * math.sin(t)) * (r + 0.004)
                    for t in [i / 32 * TAU for i in range(32)]]
            part(tube(f"Nyx vambrace ring {label}", ring, [0.0026] * 32, [M["platinum"]], n=6,
                      closed=True, per=1), ("rigid", {f"Forearm.{label}": 1.0}))
        glow_line = [a0.lerp(a1, t) + out * (0.0455 - 0.004 * math.sin(t * math.pi)) for t in [i / 12 for i in range(13)]]
        part(tube(f"Nyx vambrace circuit {label}", glow_line, [0.0017] * 13, [M["inlay"]], n=6),
             ("rigid", {f"Forearm.{label}": 1.0}))
        build_hand(M, side, label, elbow, wrist)


def rotate(v, axis, angle):
    return Matrix.Rotation(angle, 3, axis.normalized()) @ v


HAND_SCALE = 1.12


def build_hand(M, side, label, elbow, wrist):
    f = ((wrist - elbow).normalized() + Vector((0, 0, -0.55))).normalized()
    n = Vector((0, 1, 0.15))
    n = (n - f * n.dot(f)).normalized()          # 掌心朝前
    s0 = f.cross(n).normalized()
    flipped = s0.x * side < 0
    s = -s0 if flipped else s0                    # 拇指一侧朝外
    knuckle = wrist + f * 0.085
    palm = tube(f"Nyx palm {label}", [wrist - f * 0.004, wrist + f * 0.045, knuckle],
                [0.024, 0.030, 0.029], [M["gauntlet"]], n=14, fx=1.0, fy=0.46, up=tuple(s))
    part(palm, ("rigid", {f"Hand.{label}": 1.0}))
    fingers = {}
    spec = (("Index", 0.020, 0.30, (0.042, 0.026, 0.020)), ("Middle", 0.007, 0.10, (0.046, 0.029, 0.021)),
            ("Ring", -0.007, -0.10, (0.043, 0.027, 0.020)), ("Pinky", -0.020, -0.30, (0.034, 0.021, 0.017)))
    for name, offset, spread, lengths in spec:
        base = knuckle + s * offset - f * 0.004
        d = rotate(f, n, spread if flipped else -spread)   # 正角度朝拇指侧张开
        pts = [base]
        for length, curl in zip(lengths, (0.12, 0.18, 0.16)):
            d = rotate(d, d.cross(n), curl)
            pts.append(pts[-1] + d * length)
        part(tube(f"Nyx finger {label} {name}", pts, [0.0096, 0.0088, 0.0074, 0.0], [M["gauntlet"]],
                  n=8, per=4), ("finger", label, name))
        fingers[name] = (base, pts[-1])
    tbase = wrist + f * 0.018 + s * 0.020 + n * 0.004
    d = (f * 0.55 + s * 0.75 + n * 0.35).normalized()
    pts = [tbase]
    for length, curl in zip((0.030, 0.024, 0.019), (0.10, 0.16, 0.14)):
        d = rotate(d, d.cross(n), curl)
        pts.append(pts[-1] + d * length)
    part(tube(f"Nyx thumb {label}", pts, [0.0094, 0.0084, 0.0070, 0.0], [M["gauntlet"]], n=8, per=4),
         ("finger", label, "Thumb"))
    fingers["Thumb"] = (tbase, pts[-1])
    # 掌心发光盘
    disc = ellipsoid(f"Nyx palm glow {label}", (0, 0, 0), (0.013, 0.013, 0.0022), [M["glow"]], 16, 8)
    rot = n.to_track_quat("Z", "Y").to_matrix().to_4x4()
    transform_obj(disc, Matrix.Translation(wrist + f * 0.046 + n * 0.0135) @ rot)
    part(disc, ("rigid", {f"Hand.{label}": 1.0}))
    # 风格化放大：手部整体绕手腕放大，关节坐标同步缩放
    scale = Matrix.Translation(wrist) @ Matrix.Scale(HAND_SCALE, 4) @ Matrix.Translation(-wrist)
    for obj, spec in PARTS:
        if obj.name.startswith((f"Nyx palm {label}", f"Nyx finger {label}", f"Nyx thumb {label}",
                                f"Nyx palm glow {label}")):
            transform_obj(obj, scale)
    fingers = {k: (scale @ a, scale @ b) for k, (a, b) in fingers.items()}
    HANDS[label] = {"wrist": wrist, "knuckle": scale @ knuckle, "f": f, "n": n, "s": s, "fingers": fingers}


# ===== 布料：开襟长袍、披风、中央垂饰 =====
SKIRT_TOP, SKIRT_OPEN, SKIRT_TAILS = 1.345, 0.38, 8
CAPE_SPAN, CAPE_TAILS = 1.55, 7


def tail_weight(u, count, jitter=0.0):
    """飘带中心为 1、两条飘带之间的缺口为 0。"""
    x = u * count
    d = abs((x % 1.0) - 0.5 - jitter * math.sin(math.floor(x) * 2.3))
    return max(0.0, 1 - 2 * d) ** 1.5


def tail_shape(u, count, tip, valley, jitter=0.0):
    return lerp(valley, tip, tail_weight(u, count, jitter))


def hash01(k, seed=0.0):
    return (math.sin(k * 12.9898 + seed * 78.233) * 43758.5453) % 1.0


def skirt_bottom(u):
    front = max(0.0, 1 - min(u, 1 - u) / 0.28)   # 靠近前襟的飘带更长
    k = min(SKIRT_TAILS - 1, int(u * SKIRT_TAILS))
    tip = lerp(0.14, 0.04, front) + 0.09 * hash01(k, 1.0)   # 只变尖端，缺口处保持连续
    return tail_shape(u, SKIRT_TAILS, tip, 0.60, 0.08)


def skirt_flow(v):
    return -0.10 * v * v


def skirt_point(u, v):
    a = SKIRT_OPEN + u * (TAU - 2 * SKIRT_OPEN)
    z = lerp(SKIRT_TOP, skirt_bottom(u), v)
    e = v ** 1.2
    rx, ry = lerp(0.142, 0.40, e), lerp(0.110, 0.34, e)
    fold = cloth_fold(a, v, 7.0, 0.006 + 0.034 * v ** 1.1, 0.8)
    edge = max(0.0, 1 - min(u, 1 - u) / 0.05) * 0.02 * v
    tip = tail_weight(u, SKIRT_TAILS, 0.08)
    curl = smoothstep(0.6, 1.0, v) * (0.055 * tip - 0.018 * (1 - tip))   # 飘带尖外翻、边缘内卷
    r = fold + edge + curl
    return Vector(((rx + r) * math.sin(a) * (1 + 0.08 * v), (ry + r) * math.cos(a) + skirt_flow(v) + 0.004, z))


def skirt_param(p):
    """由位置反求 (u, v)，考虑向后飘动的偏移（迭代两次）。"""
    y, v = p.y, 0.5
    for _ in range(3):
        a = math.atan2(p.x, y - 0.004) % TAU
        u = clamp((a - SKIRT_OPEN) / (TAU - 2 * SKIRT_OPEN))
        v = clamp((SKIRT_TOP - p.z) / max(1e-4, SKIRT_TOP - skirt_bottom(u)))
        y = p.y - skirt_flow(v)
    return u, v


def cape_bottom(u):
    center = 1 - abs(u - 0.5) * 2
    k = min(CAPE_TAILS - 1, int(u * CAPE_TAILS))
    tip = lerp(0.14, 0.03, center) + 0.10 * hash01(k, 3.0)
    return tail_shape(u, CAPE_TAILS, tip, 0.50, 0.06)


def cape_flow(v):
    return -0.16 * v ** 1.6


def cape_top(u):
    a = math.pi - CAPE_SPAN + u * 2 * CAPE_SPAN
    return 1.765 - 0.02 * max(0.0, -math.cos(a))


def cape_point(u, v):
    a = math.pi - CAPE_SPAN + u * 2 * CAPE_SPAN
    z = lerp(cape_top(u), cape_bottom(u), v)
    e = v ** 1.1
    rx, ry = lerp(0.245, 0.62, e), lerp(0.145, 0.50, e)
    fold = cloth_fold(a, v, 5.0, 0.008 + 0.050 * v, 2.4)
    tip = tail_weight(u, CAPE_TAILS, 0.06)
    fold += smoothstep(0.6, 1.0, v) * (0.06 * tip - 0.02 * (1 - tip))
    return Vector(((rx + fold) * math.sin(a), (ry + fold) * math.cos(a) + cape_flow(v) - 0.02, z))


def cape_param(p):
    y, v = p.y, 0.5
    for _ in range(3):
        a = math.atan2(p.x, y + 0.02) % TAU
        u = clamp((a - (math.pi - CAPE_SPAN)) / (2 * CAPE_SPAN))
        v = clamp((cape_top(u) - p.z) / max(1e-4, cape_top(u) - cape_bottom(u)))
        y = p.y - cape_flow(v)
    return u, v


TABARD_TOP, TABARD_TIP = 1.44, 0.035
TABARD_Y = [(0, 0.098), (0.08, 0.120), (0.2, 0.127), (0.5, 0.122), (1.0, 0.070)]


def tabard_width(v):
    return 0.15 * (1 - 0.3 * v) * min(1.0, (1 - v) / 0.1) ** 0.7


def tabard_point(u, v):
    w = tabard_width(v)
    x = (u - 0.5) * w
    y = interp(TABARD_Y, v) - 1.2 * x * x + 0.004 * math.sin(u * math.pi * 3 + v * 4) * v
    return Vector((x, y, lerp(TABARD_TOP, TABARD_TIP, v)))


def radial_out(p, d):
    return p + Vector((p.x, p.y, 0)).normalized() * d


def build_cloth(M):
    mats = [M["cloth"], M["lining"]]
    # UV 横向按周长/高度比例拉开，保证电路线在布面上保持 45° 与等宽
    skirt = surface("Nyx robe", skirt_point, 112, 60, mats, uvfn=lambda u, v: (u * 1.6, 1 - v))
    orient(skirt, axis_ref)
    solidify(skirt, 0.007, 0, inner_offset=1)
    part(apply_all(skirt), ("skirt",))
    cape = surface("Nyx cape", cape_point, 98, 64, mats, uvfn=lambda u, v: (0.3 + u * 0.85, 1 - v))
    orient(cape, axis_ref)
    solidify(cape, 0.007, 0, inner_offset=1)
    part(apply_all(cape), ("cape",))
    tabard = surface("Nyx tabard", tabard_point, 18, 64, [M["tabard"], M["lining"]])
    orient(tabard, lambda c: Vector((0, 0, c.z)))
    solidify(tabard, 0.006, 0, inner_offset=1)
    part(apply_all(tabard), ("tabard",))
    # 下摆发光滚边与前襟 / 侧边铂金滚边
    hem = [radial_out(skirt_point(i / 263, 1.0), 0.005) for i in range(264)]
    part(tube("Nyx robe hem glow", hem, [0.0028] * 264, [M["hem"]], n=6, per=1), ("skirt",))
    cape_hem = [radial_out(cape_point(i / 223, 1.0), 0.005) for i in range(224)]
    part(tube("Nyx cape hem glow", cape_hem, [0.0028] * 224, [M["hem"]], n=6, per=1), ("cape",))
    for u in (0.0, 1.0):
        edge = [radial_out(skirt_point(u, j / 60), 0.004) for j in range(61)]
        part(tube(f"Nyx robe placket {u}", edge, [0.0036] * 61, [M["platinum"]], n=6, per=1), ("skirt",))
        cedge = [radial_out(cape_point(u, j / 60), 0.004) for j in range(61)]
        part(tube(f"Nyx cape edge {u}", cedge, [0.0034] * 61, [M["platinum"]], n=6, per=1), ("cape",))
        tedge = [tabard_point(u, j / 60) + Vector((0, 0.003, 0)) for j in range(61)]
        part(tube(f"Nyx tabard edge {u}", tedge, [0.0030] * 61, [M["platinum"]], n=6, per=1), ("tabard",))
    spine = [tabard_point(0.5, j / 40) + Vector((0, 0.0035, 0)) for j in range(4, 40)]
    part(tube("Nyx tabard spine", spine, [0.0019] * len(spine), [M["inlay"]], n=6, per=1), ("tabard",))
    # 披风背后中线的发光脊线 + 向下的人字分支（呼应中央垂饰）
    back = [radial_out(cape_point(0.5, 0.10 + i * 0.0134), 0.006) for i in range(67)]
    part(tube("Nyx cape spine", back, [0.0022] * len(back), [M["inlay"]], n=6, per=1), ("cape",))
    for j, v0 in enumerate((0.44, 0.57, 0.70, 0.83)):
        for sgn in (-1, 1):
            pts = [radial_out(cape_point(0.5 + sgn * du, v0 - du * 1.3), 0.006)
                   for du in [i * 0.0065 for i in range(9)]]
            part(tube(f"Nyx cape chevron {j} {sgn}", pts, [0.0018] * 9, [M["inlay"]], n=6, per=1), ("cape",))


# ===== 光环（骨骼子物体，网页端绕环法线旋转）=====
HALO_C = Vector((0, -0.20, 2.02))


def build_halo(M):
    objs = []
    radius = 0.30

    def at(theta, r):
        return Vector((math.sin(theta) * r, 0, math.cos(theta) * r))

    for k in range(4):
        c = k * math.pi / 2
        arc = [at(c + t, radius) for t in [(-0.56 + i * 1.12 / 24) for i in range(25)]]
        rad = [0.0, 0.6] + [1.0] * 21 + [0.6, 0.0]
        objs.append(tube(f"Nyx halo arc {k}", arc, rad, [M["halo"]], n=4, fx=0.0055, fy=0.014,
                         up=(0, 1, 0), twist=math.pi / 4, per=2))
        length = (0.15, 0.085, 0.06, 0.085)[k]
        d = at(c, 1.0)
        objs.append(tube(f"Nyx halo spike {k}", [d * (radius + 0.004), d * (radius + length)],
                         [0.012, 0.0], [M["platinum"]], n=4, fx=0.40, fy=1.0, up=(0, 1, 0),
                         twist=math.pi / 4, per=1))
        g = at(c + math.pi / 4, radius - 0.008)
        objs.append(ellipsoid(f"Nyx halo node {k}", g, (0.011,) * 3, [M["glow"]], 14, 10))
    wire = [at(i / 64 * TAU, 0.266) for i in range(64)]
    objs.append(tube("Nyx halo wire", wire, [0.0022] * 64, [M["platinum"]], n=6, closed=True, per=1))
    for i in range(16):
        d = at(i / 16 * TAU + math.pi / 16, 1.0)
        objs.append(tube(f"Nyx halo tick {i}", [d * 0.272, d * 0.284], [0.0019, 0.0019], [M["platinum"]],
                         n=4, per=1))
    return join(objs, "NYX_HALO", HALO_C)


def join(objs, name, location):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = objs[0]
    obj.name = name
    obj.location = location
    return obj


# ===== 单枚针刃（网页端克隆出 19 枚环绕）=====
NEEDLE_PROFILE = [(-0.090, 0.0), (-0.060, 0.55), (-0.042, 1.0), (0.0, 0.92), (0.14, 0.60), (0.285, 0.0)]


def build_needle(M):
    ys = [y for y, _ in NEEDLE_PROFILE]
    ws = [w * 0.019 for _, w in NEEDLE_PROFILE]
    core = tube("Nyx needle core", [(0, y, 0) for y in ys], ws, [M["needle"]], n=4, fx=0.35, fy=1.0,
                up=(0, 0, 1), per=4)
    objs = [core]
    for side in (-1, 1):
        edge = [(side * w * 1.02, y, 0) for y, w in zip(ys[1:-1], ws[1:-1])]
        edge = [(0, ys[0] + 0.012, 0)] + edge + [(0, ys[-1] - 0.004, 0)]
        objs.append(tube(f"Nyx needle edge {side}", edge, [0.0014] * len(edge), [M["hem"]], n=5, per=4))
    return join(objs, "NYX_NEEDLE", Vector((0.78, 0.05, 1.55)))


def build_all(M):
    build_torso(M)
    build_mask(M)
    build_hood(M)
    build_armor(M)
    build_pauldrons(M)
    build_arms(M)
    build_cloth(M)
    halo = build_halo(M)
    needle = build_needle(M)
    return halo, needle
