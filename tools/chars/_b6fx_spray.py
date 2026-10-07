"""Boss 6（剧毒三位体）毒雾特效私有模块：材质、毒雾羽流、飞溅毒滴、喷口光晕。

为什么重做：旧毒雾是 9 根 5 边截面的流线管 + 14 个不透明小球，材质 venom spray glow 是不透明的浅绿自发光，
读出来像一把扁平的纸片 / 玻璃刃。新毒雾全部是半透明薄片 / 薄壳，没有实心体，整束只占一个图集材质（一个图元）：
    - 外层雾壳：圆锥形开口壳（环向 14 段 × 沿喷流 10 段），贴图是湍流斑驳的深翠绿雾，向雾梢渐隐；
    - 内层雾壳：半径 0.62 倍的较亮壳，贴图是沿流向的螺旋丝，与外壳反向扭转；
    - 喷流芯壳：很窄的细壳，只在近喷口约 60% 束长处，快速流线、最亮；
    - 宽雾片：5 片穿过雾轴的平面片（36° 间隔、轻微扭转与蛇行），给雾团中心加厚、让任何视角都有体积感；
    - 窄亮片：2 片更窄的亮丝片（交叉）；
    - 喷口光晕：喷口处 3 片交叉圆盘（与整束一起随 Spray 骨放大，静止时缩在口腔里不可见）；
    - 毒滴：若干两片十字交叉的水滴形薄片（圆头朝前、尖尾拖在身后，带高光），沿喷射方向散在雾团内外。
几何都建在 Spray 骨的局部系里（+Y 为喷射方向，单位同旧版：L 为束长），调用方整体乘 SPRAY_K 并挂 Spray 骨，
动作仍由 Spray{L,C,R} 的缩放驱动（骨名与缩放驱动不变）。

材质：baseColorTexture（压暗、带 alpha）+ emissiveTexture（预乘 alpha、全亮）两张图，强度 <= 2.5，
glTF 导出为 alphaMode=BLEND + doubleSided，three.js 里自动 transparent + depthWrite=false。
材质名仍含 glow（venom spray glow）：LOD 减面跳过、游戏端按名字做辉光权重。
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from kit.core import TAU, bm_object

from chars import _b6fx_maps as MAPS

STRENGTH = 2.0          # 自发光强度（<= 2.5；亮度靠渐隐层与细芯表现，不做整块高亮）
R_END = 0.30           # 外壳在雾梢处的半径 / 束长（约 ±13°，比旧的 ±15° 扇面略窄但更厚）


# ===== 材质 =====
def spray_material(name, strength=STRENGTH):
    """半透明自发光毒雾材质（图集）。"""
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


# ===== 小工具 =====
_uv = MAPS.uv


def _hash(k, salt=0.0):
    """确定性伪随机 [0, 1)。"""
    return (math.sin(k * 12.9898 + salt * 78.233 + 4.1) * 43758.5453) % 1.0


def radius_env(v, r_end):
    """外壳半径包络：喷口处很细，随流向快速展开、后段放缓（湍流射流的锥形扩散），雾梢略收。"""
    return r_end * (0.030 + 0.970 * v ** 0.90) * (1.0 - 0.10 * MAPS.sstep(0.80, 1.0, np.float64(v)))


def shell(bm, uvl, L, r_end, k_r, tile, nu, nv, twist, wob, seed, v_end=1.0, rot=0.0, r_pow=1.0, flip=False):
    """沿 +Y 的圆锥形开口壳：环向 nu 段（多留一列接缝顶点，UV u 从 0 到 1，贴图环向周期故无缝），沿流向 nv 段。
    k_r 为相对外壳的半径系数，v_end 为壳长占束长的比例（贴图的 v 仍按壳自身 0..1），twist 为到末端累计的扭转角，
    wob 为轴线蛇行幅度（占半径比例）。"""
    rows = []
    for j in range(nv + 1):
        t = j / nv
        v = t * v_end
        y = L * v
        # 半径随位置轻微起伏（湍流鼓包），不同壳用不同相位
        puff = 1.0 + 0.10 * math.sin(seed * 1.7 + t * 9.0) + 0.06 * math.sin(seed * 3.1 + t * 17.0)
        r = L * radius_env(v, r_end) * k_r * puff ** r_pow
        cx = wob * L * radius_env(v, r_end) * math.sin(seed + t * 4.4) * t
        cz = wob * L * radius_env(v, r_end) * math.cos(seed * 1.3 + t * 3.7) * t
        ring = []
        for i in range(nu + 1):
            ph = TAU * i / nu + twist * t + rot
            # 环向半径微扰（让壳截面不是正圆）
            rr = r * (1.0 + 0.10 * math.sin(3 * ph + seed + t * 5.0) + 0.07 * math.sin(5 * ph + seed * 2.0 - t * 7.0)
                      + 0.04 * math.sin(8 * ph + seed * 3.0 + t * 11.0))
            ring.append(bm.verts.new((cx + rr * math.cos(ph), y, cz + rr * math.sin(ph))))
        rows.append(ring)
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
            for loop, (uu, vv) in zip(f.loops, ((i / nu, j / nv), ((i + 1) / nu, j / nv), ((i + 1) / nu, (j + 1) / nv),
                                               (i / nu, (j + 1) / nv))):
                loop[uvl].uv = _uv(tile, 1 - uu if flip else uu, vv)


def sheet(bm, uvl, L, r_end, k_w, tile, theta, twist, wob, seed, nv=14, v_end=1.0, flip=False):
    """穿过雾轴的平面带状片：宽度 = 2 × 外壳半径 × k_w，沿流向 nv 段（横向一格，形状全靠贴图 alpha）。
    theta 为片所在平面绕雾轴的朝向，twist 为到末端累计的扭转角，wob 为沿片法向的蛇行（占半径比例）。"""
    rows = []
    for j in range(nv + 1):
        t = j / nv
        v = t * v_end
        phi = theta + twist * t
        side = Vector((math.cos(phi), 0.0, math.sin(phi)))
        nrm = Vector((-math.sin(phi), 0.0, math.cos(phi)))
        w = L * radius_env(v, r_end) * k_w
        cen = Vector((0.0, L * v, 0.0)) + nrm * (wob * w * math.sin(seed + t * 5.0) * t)
        rows.append((bm.verts.new(cen - side * w), bm.verts.new(cen + side * w)))
    for j in range(nv):
        f = bm.faces.new((rows[j][0], rows[j][1], rows[j + 1][1], rows[j + 1][0]))
        u0, u1 = (1, 0) if flip else (0, 1)
        for loop, (uu, vv) in zip(f.loops, ((u0, j), (u1, j), (u1, j + 1), (u0, j + 1))):
            loop[uvl].uv = _uv(tile, uu, vv / nv)


def disc(bm, uvl, center, ax1, ax2, r1, r2, tile=MAPS.HALO):
    """一块方形片（贴图自身是 r<1 的圆盘光斑）：中心 center，半边长 r1 / r2，沿 ax1 / ax2。"""
    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    vs = [bm.verts.new(center + ax1 * (x * r1) + ax2 * (y * r2)) for x, y in corners]
    f = bm.faces.new(vs)
    for loop, (x, y) in zip(f.loops, corners):
        loop[uvl].uv = _uv(tile, (x + 1) / 2, (y + 1) / 2)


def droplet(bm, uvl, center, d, size):
    """水滴：两片十字交叉的水滴形薄片，圆头朝前（沿 d）。size 为薄片宽度，长 = 1.7 × 宽，圆头在片长 68% 处。"""
    d = Vector(d).normalized()
    a = d.orthogonal().normalized()
    c = d.cross(a)
    Lq = 1.7 * size
    for ax in (a, c):
        # 以圆头圆心（v=0.68）为锚点，让水滴围绕 center 摆放
        p0 = center - d * (0.68 * Lq)
        vs = [bm.verts.new(p0 - ax * (size / 2)), bm.verts.new(p0 + ax * (size / 2)),
              bm.verts.new(p0 + ax * (size / 2) + d * Lq), bm.verts.new(p0 - ax * (size / 2) + d * Lq)]
        f = bm.faces.new(vs)
        for loop, (uu, vv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uvl].uv = _uv(MAPS.DROP, uu, vv)


# ===== 一束毒雾 =====
def venom_plume(name, L, mat, seed=0.0):
    """一束毒雾（单网格、单材质）。局部系：原点为喷口，+Y 为喷射方向，L 为满伸束长。"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rot = seed * 0.9
    # 外轮廓由“宽雾片”扇面定义（片的横向是高斯渐隐 + 撕裂边，没有环壳的掠射硬边）：7 片绕雾轴 ~26° 间隔，
    # 宽度、长度、扭转、蛇行各异，奇数片翻转贴图
    for i in range(8):
        h1, h2, h3 = _hash(i, seed), _hash(i, seed + 3.0), _hash(i, seed + 7.0)
        sheet(bm, uvl, L, R_END, 0.95 + 0.30 * h1, MAPS.BILLOW_A, rot + i * math.pi / 8 + 0.1 * h2,
              twist=(0.9 * h3 - 0.45) * 1.6, wob=0.40, seed=seed + i * 1.9, flip=bool(i % 2),
              v_end=0.88 + 0.10 * h2)
    # 中层雾壳：较淡的湍流壳，给雾团内部的斑驳（半径 0.62，不参与外轮廓）
    shell(bm, uvl, L, R_END, 0.62, MAPS.MIST_A, 14, 10, twist=-0.9, wob=0.12, seed=seed + 5.1, rot=rot + 0.4, flip=True,
          v_end=0.92)
    # 内层雾壳：较亮的螺旋丝，反向扭转
    shell(bm, uvl, L, R_END, 0.40, MAPS.MIST_B, 12, 10, twist=-1.4, wob=0.14, seed=seed + 1.7, rot=rot + 0.5,
          v_end=0.84)
    # 喷流芯壳：细、近喷口最亮
    shell(bm, uvl, L, R_END, 0.16, MAPS.JET, 8, 8, twist=0.9, wob=0.06, seed=seed + 2.9, rot=rot + 0.2, v_end=0.62)
    # 窄亮片：2 片交叉，亮丝
    for i in range(2):
        sheet(bm, uvl, L, R_END, 0.36, MAPS.BILLOW_B, rot + 0.35 + i * math.pi / 2, twist=-0.8, wob=0.25,
              seed=seed + 4.1 + i * 2.3, flip=bool(i), v_end=0.66)
    # 喷口光晕：垂直于喷射方向的一块 + 两块含轴的交叉圆盘
    r0 = 0.060 * L
    disc(bm, uvl, Vector((0, 0.03 * L, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), r0, r0)
    disc(bm, uvl, Vector((0, 0.10 * L, 0)), Vector((0, 1, 0)), Vector((1, 0, 0)), r0 * 1.6, r0)
    disc(bm, uvl, Vector((0, 0.10 * L, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), r0 * 1.6, r0)
    # 毒滴：散在雾团内外，沿着从喷口向外的方向拉长（圆头朝前）
    n = 9
    for k in range(n):
        az = TAU * _hash(k, 3)
        dist = L * (0.30 + 0.78 * _hash(k, 4) ** 0.8)
        ang = 0.06 + 0.26 * (dist / L) * (0.4 + 0.9 * _hash(k, 5))
        lat = Vector((math.cos(az), 0.0, math.sin(az))) * (math.sin(ang) * dist)
        c = Vector((0.0, math.cos(ang) * dist, 0.0)) + lat
        d = c.normalized()
        size = L * (0.021 + 0.024 * _hash(k, 6))
        droplet(bm, uvl, c, d, size)
    return bm_object(name, bm, [mat], smooth=False)


# ===== 统计 =====
def tris_of(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)
