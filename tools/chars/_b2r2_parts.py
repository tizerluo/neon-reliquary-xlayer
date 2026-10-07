"""Boss 2（钢铁巨兽）第二轮私有工具：半透明火舌、齿轮徽记、壳片、分节角、爪、统计。

不改 kit 与 _bossA_common（后者被 Boss 0 / Boss 1 共用）：
- _bossA_common.flame 是一个不透明的实心花瓣锥，在 AgX 下像塑料尖角。这里的 flame_sheets() 改成
  几片交叉的细长薄片（双面、alpha 渐隐），配 RGBA 贴图（u 向两侧渐隐、v 向尖端渐隐，核心偏黄白、
  边缘与尖端偏深红）。材质用 Principled 的 Alpha 接贴图 alpha：Cycles 渲染透明正常，glTF 导出为
  alphaMode=BLEND + doubleSided，three.js 里 transparent + depthWrite=false。
- gear_plate / emblem 做浮雕齿轮徽记（黄铜齿圈 + 深色凹盘 + 琥珀轴帽 + 辐条）。
- dome_lame 是椭球壳片（肩胛 / 髋部叠甲的一层），lip 沿边缘可取点做滚边与铆钉。
- tris_report 按材质统计三角面，便于控制游戏版预算。
"""

import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from kit.core import TAU, bm_object, box_blur, lerp, plate, smoothstep, surface, trim, tube

from chars._bossA_common import studs


# ===== 半透明火舌 =====
def flame_maps(size=128, hot=(1.0, 0.80, 0.38), mid=(1.0, 0.42, 0.07), edge=(0.78, 0.10, 0.012), seed=3, core=1.0):
    """火舌贴图（RGBA）：u 横向、v 纵向（第 0 行为底 v=0）。alpha = 横向软边 × 纵向渐隐 × 纵向条纹；
    颜色随“核心度”在 边缘深红 → 中段橙 → 核心黄白 之间渐变。core 越大越偏亮（内焰用）。"""
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, size, dtype=np.float32)[:, None] * np.ones((1, size), np.float32)
    u = np.linspace(0, 1, size, dtype=np.float32)[None, :] * np.ones((size, 1), np.float32)
    x = np.abs(2 * u - 1)
    soft = np.clip(1 - x ** 2.4, 0, 1) ** 0.9
    noise = box_blur(rng.random((size, size)).astype(np.float32), 5)
    noise = (noise - noise.min()) / max(1e-6, noise.max() - noise.min())
    streak = 0.72 + 0.28 * np.sin(TAU * (u * 3.0 + v * 1.3 + noise * 0.9)) ** 2
    rise = np.clip(v / 0.06, 0, 1)
    fade = rise * np.clip(1 - v, 0, 1) ** 1.35
    wisp = box_blur(rng.random((size, size)).astype(np.float32), 3)
    wisp = np.clip((wisp - wisp.min()) / max(1e-6, wisp.max() - wisp.min()) * 1.6 - 0.2, 0, 1)
    alpha = np.clip(soft * fade * streak * (0.55 + 0.45 * wisp) * 1.25, 0, 1) * 0.60
    t = np.clip(soft ** 1.6 * np.clip(1 - v * 0.8, 0, 1) * core * (0.7 + 0.3 * streak), 0, 1)
    lo = np.clip(t * 2.0, 0, 1)[..., None]
    hi = np.clip(t * 2.0 - 1.0, 0, 1)[..., None]
    c0, c1, c2 = (np.array(c, np.float32)[None, None, :] for c in (edge, mid, hot))
    rgb = c0 * (1 - lo) + c1 * lo
    rgb = rgb * (1 - hi) + c2 * hi
    return np.concatenate([rgb, alpha[..., None]], axis=2).astype(np.float32)


def flame_material(name, rgba, strength=3.0):
    """半透明自发光材质：同一张 RGBA 贴图接 Base Color / Emission Color / Alpha（glTF 导出只认同图 alpha）。"""
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(f"{name} rgba", width=w, height=h, alpha=True)
    img.pixels.foreach_set(np.clip(rgba, 0, 1).ravel())
    img.alpha_mode = "STRAIGHT"
    img.pack()
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
    nt.links.new(tex.outputs["Alpha"], p.inputs["Alpha"])
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


def flame_sheets(name, base, direction, height, width, mats, n=4, seed=0.0, nu=5, nv=13, lean=0.0):
    """一束细长的火舌薄片：n 片绕轴交叉、高度 / 宽度各异，窄而长，路径带轻微摆动与前倾。
    UV：u 横跨薄片、v 自底向尖端 0→1。双面材质，本体不做实心。"""
    b = Vector(base)
    d = Vector(direction).normalized()
    a = d.orthogonal().normalized()
    c = d.cross(a)
    rng = random.Random(int(seed * 1000) + 7)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for k in range(n):
        ang = k / n * math.pi + seed * 0.7
        side = a * math.cos(ang) + c * math.sin(ang)
        other = -a * math.sin(ang) + c * math.cos(ang)
        hk = height * (0.62 + 0.38 * rng.random())
        wk = width * (0.75 + 0.5 * rng.random())
        ph = rng.random() * TAU
        rows = []
        for j in range(nv):
            v = j / (nv - 1)
            body = (1 - v) ** 0.8 * (0.55 + 0.45 * math.sin(math.pi * min(1.0, v * 1.5 + 0.25)))
            wob = 0.16 * wk * math.sin(ph + v * 5.2) * v
            curl = (0.10 * hk * v ** 1.6 + lean * hk * v ** 2) * (1 if k % 2 else -0.6)
            cen = b + d * (hk * v) + side * wob + other * curl
            row = []
            for i in range(nu):
                u = i / (nu - 1)
                row.append(bm.verts.new(cen + side * (wk * body * (2 * u - 1))))
            rows.append(row)
        for j in range(nv - 1):
            for i in range(nu - 1):
                f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
                for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    loop[uvl].uv = (ii / (nu - 1), jj / (nv - 1))
    return bm_object(name, bm, mats, smooth=False)


# ===== 齿轮徽记 =====
def gear_outline(r_out, r_root, teeth, tooth=0.30):
    pts = []
    d = TAU / teeth
    for i in range(teeth):
        a = i * d
        for off, r in ((-tooth * 0.5 - 0.10, r_root), (-tooth * 0.5, r_out), (tooth * 0.5, r_out),
                       (tooth * 0.5 + 0.10, r_root)):
            ang = a + off * d
            pts.append((math.cos(ang) * r, math.sin(ang) * r))
    return pts


def plane_axes(normal, hint=(0, 0, 1)):
    """由法向与参考向上方向求面内正交轴 (x, y)，使 x × y = normal。"""
    n = Vector(normal).normalized()
    h = Vector(hint)
    y = h - n * h.dot(n)
    if y.length < 1e-4:
        y = Vector((0, 1, 0)) - n * n.y
    y.normalize()
    x = y.cross(n)
    return x, y


def emblem(name, center, normal, r, mats, teeth=12, hint=(0, 0, 1), depth=0.05, hub=None, spokes=6, brass=None):
    """浮雕齿轮徽记：返回 [部件对象...]。mats = dict(gear=, disc=, hub=, trim=, spoke=)。
    center 为基面中心，normal 朝外；齿圈厚 depth，凹盘略低、轴帽凸起。"""
    c, n = Vector(center), Vector(normal).normalized()
    xa, ya = plane_axes(n, hint)
    out = []
    out.append(plate(f"{name} gear", gear_outline(r, r * 0.80, teeth), depth, [mats["gear"]], origin=c + n * depth * 0.5,
                     xaxis=xa, yaxis=ya, bev=depth * 0.22, bev_seg=1))
    ring = [c + n * depth * 1.12 + (xa * math.cos(q / 20 * TAU) + ya * math.sin(q / 20 * TAU)) * r * 0.66
            for q in range(20)]
    out.append(trim(f"{name} ring", ring, depth * 0.36, mats["trim"], closed=True, n=4))
    disc = [(math.cos(q / 20 * TAU) * r * 0.60, math.sin(q / 20 * TAU) * r * 0.60) for q in range(20)]
    out.append(plate(f"{name} disc", disc, depth * 0.5, [mats["disc"]], origin=c + n * depth * 0.95, xaxis=xa, yaxis=ya))
    for q in range(spokes):
        t = q / spokes * TAU
        d = xa * math.cos(t) + ya * math.sin(t)
        out.append(tube(f"{name} spoke {q}", [c + n * depth * 1.35 + d * r * 0.16, c + n * depth * 1.35 + d * r * 0.58],
                        [depth * 0.40, depth * 0.34], [mats["spoke"]], n=3, per=1))
    if hub is not None:
        ctr = c + n * depth * 1.5
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
        for v in bm.verts:
            v.co = ctr + xa * (v.co.x * r * 0.20) + ya * (v.co.y * r * 0.20) + n * (v.co.z * r * 0.13)
        out.append(bm_object(f"{name} hub", bm, [hub]))
    return out


# ===== 椭球壳片（肩胛 / 髋部叠甲） =====
def dome_point(P, out, rx, ry, rz, th, phi, tilt=0.0):
    """壳片参数点：th 从外侧水平 0 转到顶部 π/2，phi 前后 -π/2..π/2；tilt 为绕 y 轴向外倾斜。"""
    cphi = math.cos(phi)
    x = out * math.cos(th) * cphi * rx
    y = math.sin(phi) * ry
    z = math.sin(th) * cphi * rz
    if tilt:
        ct, st = math.cos(tilt), math.sin(tilt)
        x, z = x * ct + out * z * st, -out * x * st + z * ct
    return Vector(P) + Vector((x, y, z))


def dome_lame(name, P, out, rx, ry, rz, th0, th1, mats, nu=16, nv=7, tilt=0.0):
    """椭球壳片曲面（法线朝外由调用方 orient）：返回对象与 (边缘取点函数)。"""
    def f(u, v):
        return dome_point(P, out, rx, ry, rz, lerp(th0, th1, v), (u - 0.5) * math.pi * 0.96, tilt)
    obj = surface(name, f, nu, nv, mats, uvfn=lambda u, v: (u * 1.5, v * 1.0))
    return obj, f


# ===== 统计 =====
def tris_report(ctx, target, keep=("glow", "core", "flame", "dial")):
    """按材质的三角面统计 + 预计游戏版减面比例（只有 >3000 面且名字不含 keep 的合并网格会被减面）。"""
    by = {}
    for o in [o for o, _ in ctx.parts] + [o for o, *_ in ctx.attached]:
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        m = o.data.materials[0].name if o.data.materials else "?"
        by[m] = by.get(m, 0) + n
    total = sum(by.values())
    kept = sum(v for k, v in by.items() if any(w in k.lower() for w in keep) or v <= 3000)
    rest = total - kept
    ratio = max(0.12, min(1.0, (target - kept) / rest)) if rest and total > target else 1.0
    print(f"TRIS {ctx.id}: total {total}  fixed {kept}  decimable {rest}  est game ratio {ratio:.3f}  "
          f"est game tris {int(kept + rest * ratio)}")
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
        print(f"    {v:7d}  {k}")
    # 按部件类（名字去掉数字 / 侧别后缀）汇总，找出最费面的类别
    import re
    cat = {}
    for o in [o for o, _ in ctx.parts] + [o for o, *_ in ctx.attached]:
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        key = re.sub(r"[-+\d.]+| [LR]\b| [lr]$", "", o.name.replace(ctx.title, "")).strip()
        mname = o.data.materials[0].name if o.data.materials else ""
        want = __import__("os").environ.get("B2_MAT", "")
        if want and want not in mname:
            continue
        cat[key] = cat.get(key, 0) + n
    for k, v in sorted(cat.items(), key=lambda kv: -kv[1])[:int(__import__("os").environ.get("B2_TOP", 0))]:
        print(f"      cat {v:7d}  {k}")
