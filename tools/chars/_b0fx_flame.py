"""Boss 0（余烬之王）特效私有模块：分层半透明火舌、火星、烧红喷口环、统计。

为什么不用 _bossA_common.flame（被 Boss 1 / 2 / 3 共用，只读不改）：它是一个不透明的实心花瓣锥，
在 AgX / ACES 下像粉橙色塑料尖角。这里改成几片交叉的细长薄片（双面、alpha 渐隐），思路来自
_b2r2_parts.flame_sheets，但贴图改成自己的图集（_b0fx_maps）：
    - 外层：3–4 片橙红火舌，高度 / 宽度各异，基部略偏离中轴，带扭转、摆动与尖端前倾，边缘由贴图撕裂；
    - 内层：1–2 片更短更窄的黄白炽热细芯；
    - 火星：几粒细长的亮点悬在火舌上方（随 Vent 骨缩放一起升高）。
每根火焰骨只出一个网格、一个材质（图集），所以 GLB 里的图元数不会比旧版多。
材质：baseColorTexture（压暗、带 alpha）+ emissiveTexture（全亮）分开两张图，
漫反射几乎不贡献，火焰靠自发光与透明度读出“光”，glTF 导出为 alphaMode=BLEND + doubleSided。
"""

import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from kit.core import TAU, bm_object, ring_points, trim

from chars import _b0fx_maps as MAPS

TILE_OUTER_A, TILE_OUTER_B, TILE_INNER, TILE_SPARK = 0, 1, 2, 3


# ===== 材质 =====
def flame_material(name, strength=2.3):
    """半透明自发光火焰材质（图集）。强度控制在 <= 2.5，亮度靠渐隐层与细芯表现，不做整块高亮。"""
    base, emit = MAPS.atlas()
    h, w = base.shape[:2]
    img_b = bpy.data.images.new(f"{name} base rgba", width=w, height=h, alpha=True)
    img_b.pixels.foreach_set(np.clip(base, 0, 1).ravel())
    img_b.alpha_mode = "STRAIGHT"
    img_b.pack()
    rgba_e = np.concatenate([emit, np.ones((h, w, 1), np.float32)], axis=2)
    img_e = bpy.data.images.new(f"{name} emit", width=w, height=h, alpha=False)
    img_e.pixels.foreach_set(np.clip(rgba_e, 0, 1).ravel())     # 注意：写完像素后不要再改色彩空间，否则缓冲被清空
    img_e.pack()
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tb = nt.nodes.new("ShaderNodeTexImage")
    tb.image = img_b
    tb.extension = "EXTEND"
    te = nt.nodes.new("ShaderNodeTexImage")
    te.image = img_e
    te.extension = "EXTEND"
    nt.links.new(tb.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(tb.outputs["Alpha"], p.inputs["Alpha"])
    nt.links.new(te.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = strength
    p.inputs["Roughness"].default_value = 1.0
    p.inputs["Specular IOR Level"].default_value = 0.0
    m.use_backface_culling = False
    m.surface_render_method = "BLENDED"
    try:
        m.use_transparent_shadow = True
    except AttributeError:
        pass
    return m


def ring_material(ctx, name, strength=1.6):
    """烧红的喷口环：深橙红自发光（色相压红、强度不高，AgX / ACES 下不会发白发粉），细管。
    名字含 glow：游戏端选择性辉光权重 0.5，细环刚好起晕。"""
    return ctx.mat("ring", name, (0.40, 0.03, 0.005), rough=0.55, emit=(1.0, 0.085, 0.008), strength=strength)


# ===== 火舌薄片 =====
def _sheet(bm, uvl, base, d, a, c, tile, height, width, theta, twist, sway, sway_dir, sway_ph, curl, curl_dir,
           off, cup, mirror, nu=5, nv=12):
    """一片火舌薄片：矩形带（宽度恒为 width，舌形轮廓全靠贴图 alpha），沿 d 升起。
    theta 为薄片平面绕轴的朝向，twist 为到尖端累计的扭转角；sway 为左右摆动、curl 为尖端前倾。
    UV：u 横跨、v 自底向尖端，落在图集第 tile 格。"""
    rows = []
    for j in range(nv):
        v = j / (nv - 1)
        phi = theta + twist * v
        side = a * math.cos(phi) + c * math.sin(phi)
        nrm = -a * math.sin(phi) + c * math.cos(phi)
        lat = sway * math.sin(sway_ph + v * 4.6) * v ** 0.8 * sway_dir
        cen = base + off * (1 - v * 0.55) + d * (height * v) + lat + curl_dir * (curl * height * v ** 1.8)
        row = []
        for i in range(nu):
            u = i / (nu - 1)
            s = 2 * u - 1
            row.append(bm.verts.new(cen + side * (width * s) + nrm * (cup * width * (1 - s * s) * (0.4 + v))))
        rows.append(row)
    for j in range(nv - 1):
        for i in range(nu - 1):
            f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                uu = 1 - ii / (nu - 1) if mirror else ii / (nu - 1)
                loop[uvl].uv = ((tile + uu) / MAPS.TILES, jj / (nv - 1))


def flame_bundle(name, base, direction, height, width, mat, seed=0.0, n_out=3, n_in=2, sparks=0, lean=1.0,
                 spark_span=1.0):
    """一束分层火舌（外层橙红 + 内层黄白细芯 + 可选火星），返回单个网格对象（单材质）。
    height / width 为主舌的高度与半宽；lean 缩放摆动与尖端前倾；spark_span 为火星升到的相对高度。"""
    b = Vector(base)
    d = Vector(direction).normalized()
    a = d.orthogonal().normalized()
    c = d.cross(a)
    rng = random.Random(int(seed * 1000) + 11)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")

    def unit(ang):
        return a * math.cos(ang) + c * math.sin(ang)

    # 外层：k=0 为居中的主舌，其余为偏向一侧、较短的侧舌（形成高低错落的舌尖）
    spin = rng.random() * TAU
    for k in range(n_out):
        main = k == 0
        hk = height * (1.0 if main else 0.55 + 0.30 * rng.random())
        wk = width * (1.0 if main else 0.62 + 0.22 * rng.random())
        ang = spin + k * TAU / max(1, n_out) + 0.6 * rng.random()
        off = Vector((0, 0, 0)) if main else unit(ang) * width * (0.30 + 0.22 * rng.random())
        theta = spin * 0.5 + k * math.pi / n_out + 0.25 * rng.random()
        twist = (0.55 + 0.45 * rng.random()) * (1 if (k + int(seed)) % 2 == 0 else -1)
        curl_dir = unit(ang) if not main else unit(spin)
        _sheet(bm, uvl, b, d, a, c, TILE_OUTER_A if k % 2 == 0 else TILE_OUTER_B, hk, wk, theta, twist,
               sway=0.10 * hk * lean, sway_dir=unit(spin + 1.9 + k), sway_ph=rng.random() * TAU,
               curl=(0.16 if main else 0.30) * lean, curl_dir=curl_dir, off=off,
               cup=(0.16 if k % 2 == 0 else -0.16), mirror=rng.random() < 0.5)
    # 内层：更短更窄的炽热细芯，与外层主舌同向，彼此交叉
    for k in range(n_in):
        hk = height * (0.60 + 0.12 * rng.random())
        wk = width * (0.50 + 0.10 * rng.random())
        _sheet(bm, uvl, b, d, a, c, TILE_INNER, hk, wk, spin * 0.5 + k * math.pi / max(1, n_in) + 0.5,
               twist=0.5 * (1 if k % 2 == 0 else -1), sway=0.06 * hk * lean, sway_dir=unit(spin + 1.9),
               sway_ph=rng.random() * TAU, curl=0.12 * lean, curl_dir=unit(spin), off=Vector((0, 0, 0)),
               cup=0.08, mirror=rng.random() < 0.5, nu=3, nv=10)
    # 火星：高处悬浮的细长亮点（小菱形薄片，朝向随机）
    for q in range(sparks):
        ang = rng.random() * TAU
        rr = width * (0.5 + 0.9 * rng.random())
        hh = height * (0.55 + 0.55 * rng.random()) * spark_span
        sl = 0.065 + 0.045 * rng.random()
        sw = 0.026 + 0.016 * rng.random()
        c0 = b + unit(ang) * rr + d * hh
        _sheet(bm, uvl, c0, d, a, c, TILE_SPARK, sl, sw, rng.random() * math.pi, twist=0.0, sway=0.0,
               sway_dir=a, sway_ph=0.0, curl=0.0, curl_dir=a, off=Vector((0, 0, 0)), cup=0.0, mirror=False, nu=3, nv=4)
    return bm_object(name, bm, [mat], smooth=False)


# ===== 烧红喷口环 =====
def vent_ring(name, center, r, tube, mat, segs=24, n=6, normal=(0, 0, 1)):
    """喷口环：一圈细管（朝向 normal），贴在喷口边缘；挂在不缩放的 Furnace 骨上，火舌升缩时环保持稳定。"""
    pts = ring_points(Vector(center), normal, r, segs)
    return trim(name, pts, tube, mat, closed=True, n=n)


# ===== 统计 =====
def tris_of(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)
