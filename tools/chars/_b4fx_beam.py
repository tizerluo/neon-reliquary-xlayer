"""Boss 4（机械神祇）光束特效私有模块：材质、能量光束、炮口充能光晕、统计。

为什么重做：旧光束（tube，材质 emitter beam glow，强度 7.0）是不透明的实心白条，Attack 时六根像筷子。
新光束是一个“光”的体积感组合，全部是薄片 / 薄环，没有实心体，只占一个图集材质：
    - 外层光晕：3 片宽而淡的琥珀金薄片（绕束轴 60° 交叉，带轻微扭转），边缘撕裂；
    - 内层光晕：3 片较窄的浅金薄片（与外层错开 30°，反向扭转），贴图里叠三股编织的能量丝；
    - 白金芯线：2 片很细的薄片（90° 交叉），最亮；
    - 脉冲环：沿束长等距的 4 个扁平圆环（环面垂直于束轴），半径随束收窄、越往末端越淡；
    - 炮口闪光：炮口处 3 片交叉的圆盘光斑（只在开火时随 Beam 骨出现）。
束端渐隐收束（宽度收窄 + 贴图 alpha 渐隐）。束向变换沿用原有的 Beam 骨缩放（Y 伸缩长度、XZ 为宽度 / 脉动）。
炮口充能光晕（muzzle_halo）是 3 片交叉圆盘，蒙到 Muzzle 骨上（随炮口蓄能缩放），与光束共用同一个材质。

材质：baseColorTexture（压暗、带 alpha）+ emissiveTexture（预乘 alpha、全亮）两张图，强度 <= 2.5，
glTF 导出为 alphaMode=BLEND + doubleSided，three.js 里自动 transparent + depthWrite=false。
材质名含 beam glow：游戏端 tuneMaterial 会把自发光乘 1.2（带 emissiveMap 的选择性辉光权重为 0.12）。
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from kit.core import TAU, bm_object

from chars import _b4fx_maps as MAPS

STRENGTH = 2.4          # 自发光强度（<= 2.5；亮度靠渐隐层与细芯表现，不做整块高亮）


# ===== 材质 =====
def beam_material(name, strength=STRENGTH):
    """半透明自发光光束材质（图集）。"""
    base, emit = MAPS.atlas()
    h, w = base.shape[:2]
    img_b = bpy.data.images.new(f"{name} base rgba", width=w, height=h, alpha=True)
    img_b.pixels.foreach_set(np.clip(base, 0, 1).ravel())
    img_b.alpha_mode = "STRAIGHT"
    img_b.pack()
    rgba_e = np.concatenate([emit, np.ones((h, w, 1), np.float32)], axis=2)
    img_e = bpy.data.images.new(f"{name} emit", width=w, height=h, alpha=False)
    img_e.pixels.foreach_set(np.clip(rgba_e, 0, 1).ravel())     # 写完像素后不要再改色彩空间，否则缓冲被清空
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


# ===== 几何小件 =====
_uv = MAPS.uv


def width_env(v):
    """束宽包络（相对 1）：炮口处略收、很快展开，末端收窄成束尖。"""
    s0 = MAPS.sstep(0.0, 0.14, np.float64(v))
    s1 = MAPS.sstep(0.50, 1.0, np.float64(v))
    return float((0.60 + 0.40 * s0) * (1 - 0.55 * s1))


def _frame(d):
    d = Vector(d).normalized()
    a = d.orthogonal().normalized()
    c = d.cross(a)
    return d, a, c


def sheet(bm, uvl, origin, d, a, c, theta, length, half, tile, twist, nv, phase=0.0, wob=0.0):
    """沿束向的一片带状薄片：宽度恒为 2×half×包络，沿束向 nv 段（横向只一格，形状全靠贴图 alpha）。
    theta 为薄片所在平面绕轴的朝向，twist 为到束端累计的扭转角，wob 为轻微的横向蛇行。"""
    rows = []
    for j in range(nv):
        v = j / (nv - 1)
        phi = theta + twist * v
        side = a * math.cos(phi) + c * math.sin(phi)
        nrm = -a * math.sin(phi) + c * math.cos(phi)
        cen = origin + d * (length * v) + nrm * (wob * math.sin(phase + v * 5.0) * half * v)
        w = half * width_env(v)
        rows.append((bm.verts.new(cen - side * w), bm.verts.new(cen + side * w)))
    for j in range(nv - 1):
        f = bm.faces.new((rows[j][0], rows[j][1], rows[j + 1][1], rows[j + 1][0]))
        for loop, (uu, vv) in zip(f.loops, ((0, j), (1, j), (1, j + 1), (0, j + 1))):
            loop[uvl].uv = _uv(tile, uu, vv / (nv - 1))


def ring(bm, uvl, center, d, a, c, r_out, width, tile, segs=20):
    """垂直于束轴的扁平圆环（环带宽 width）：UV u 环向 0..1、v 径向（内缘 0 → 外缘 1）。"""
    r_in = max(0.01, r_out - width)
    verts = []
    for i in range(segs):
        t = TAU * i / segs
        rad = a * math.cos(t) + c * math.sin(t)
        verts.append((bm.verts.new(center + rad * r_in), bm.verts.new(center + rad * r_out)))
    for i in range(segs):
        j = (i + 1) % segs
        f = bm.faces.new((verts[i][0], verts[i][1], verts[j][1], verts[j][0]))
        for loop, (uu, vv) in zip(f.loops, ((i / segs, 0), (i / segs, 1), ((i + 1) / segs, 1), ((i + 1) / segs, 0))):
            loop[uvl].uv = _uv(tile, uu, vv)


def disc(bm, uvl, center, ax1, ax2, r1, r2, tile=MAPS.HALO):
    """一块方形片（贴图自身是 r<1 的圆盘光斑）：中心 center，半边长 r1 / r2，沿 ax1 / ax2。"""
    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    vs = [bm.verts.new(center + ax1 * (x * r1) + ax2 * (y * r2)) for x, y in corners]
    f = bm.faces.new(vs)
    for loop, (x, y) in zip(f.loops, corners):
        loop[uvl].uv = _uv(tile, (x + 1) / 2, (y + 1) / 2)


# ===== 光束 =====
def energy_beam(name, origin, direction, length, k, mat, seed=0.0):
    """一根能量光束（单网格、单材质）。origin 为炮口，direction 为束向，length 为束长，k 为尺寸系数（缩放半宽）。
    半宽：外层光晕 0.26k、内层光晕 0.13k、芯线 0.05k。"""
    o = Vector(origin)
    d, a, c = _frame(direction)
    rot = seed * 1.7
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    # 外层光晕：3 片，60° 交叉，轻微同向扭转
    for i in range(3):
        sheet(bm, uvl, o, d, a, c, rot + i * math.pi / 3, length, 0.26 * k, MAPS.GLOW_A, twist=0.9, nv=18,
              phase=seed + i * 2.1, wob=0.25)
    # 内层光晕：3 片，与外层错开 30°，反向扭转（与编织丝贴图一起读出能量绞缠）
    for i in range(3):
        sheet(bm, uvl, o, d, a, c, rot + math.pi / 6 + i * math.pi / 3, length, 0.13 * k, MAPS.GLOW_B, twist=-1.5, nv=18,
              phase=seed + i * 1.3)
    # 芯线：2 片，90° 交叉，笔直
    for i in range(2):
        sheet(bm, uvl, o, d, a, c, rot + 0.4 + i * math.pi / 2, length, 0.055 * k, MAPS.CORE, twist=0.0, nv=12)
    # 脉冲环：沿束长等距的 4 个扁环，半径随包络收窄、越靠末端越淡越细（贴在外层光晕边缘，不抢束体）
    for i, v in enumerate((0.17, 0.35, 0.53, 0.71)):
        r_out = 0.23 * k * width_env(v)
        ring(bm, uvl, o + d * (length * v), d, a, c, r_out, 0.095 * k * (1.0 - 0.12 * i),
             MAPS.RING_A if i < 2 else MAPS.RING_B)
    # 炮口闪光：垂直于束轴的一块 + 两块含束轴的交叉圆盘（只在开火时随 Beam 骨出现）
    disc(bm, uvl, o + d * (0.03 * k), a, c, 0.26 * k, 0.26 * k)
    disc(bm, uvl, o + d * (0.10 * k), d, a, 0.22 * k, 0.24 * k)
    disc(bm, uvl, o + d * (0.10 * k), d, c, 0.22 * k, 0.24 * k)
    return bm_object(name, bm, [mat], smooth=False)


# ===== 炮口充能光晕 =====
def muzzle_halo(name, center, direction, r, mat):
    """炮口充能光晕：3 片交叉圆盘（1 片垂直于炮轴、2 片含炮轴），在炮口光球周围起一圈柔光；挂 Muzzle 骨。"""
    d, a, c = _frame(direction)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    ctr = Vector(center)
    disc(bm, uvl, ctr, a, c, r, r)
    disc(bm, uvl, ctr, d, a, r, r)
    disc(bm, uvl, ctr, d, c, r, r)
    return bm_object(name, bm, [mat], smooth=False)


# ===== 统计 =====
def tris_of(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)
