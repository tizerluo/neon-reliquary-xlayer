"""掉落道具 · 低面数几何构建器（由 tools/blades/geo.py 复制扩展，不依赖飞剑模块）。

纯 Python 顶点 / 面表 → Blender 网格。坐标约定（Blender，Z 向上，导出 glTF 后 Y 向上）。
法线统一在建面时按“内部参考点”定向，不依赖 bmesh 重算。相比飞剑版新增：
  frame()  把局部 Z 轴对齐到任意方向放置（宝石、圆柱、尖顶）；
  lathe()  车削体；box()  长方体；rib()  沿路径的小截面滚边；ribbon()  贴面窄带（发光电路线）。
"""

import math
from contextlib import contextmanager

import bpy
from mathutils import Matrix, Vector


# ===== 颜色 / 材质 =====
def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(hexcolor):
    """#rrggbb（sRGB）→ 线性 RGB 三元组。"""
    h = hexcolor.lstrip("#")
    return tuple(_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def make_material(name, base, metal=0.0, rough=0.5, emit=None, strength=0.0, spec=0.5, alpha=1.0, cull=False):
    """纯色 Principled 材质；alpha < 1 时按“混合 + 双面”设置（导出时再补 glTF 的 BLEND / doubleSided）。
    cull=True → 背面剔除（导出为 doubleSided=false；只给已经用 cullcheck 验过的封闭实体用，如碎片）。"""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    p = m.node_tree.nodes["Principled BSDF"]

    def put(key, value):
        if key in p.inputs:
            p.inputs[key].default_value = value

    put("Base Color", (*lin(base), 1))
    put("Metallic", metal)
    put("Roughness", rough)
    put("Specular IOR Level", spec)
    put("Alpha", alpha)
    if emit:
        put("Emission Color", (*lin(emit), 1))
        put("Emission Strength", strength)
    else:
        put("Emission Strength", 0.0)
    m.diffuse_color = (*lin(base), alpha)
    m.use_backface_culling = bool(cull)
    if alpha < 1.0:
        try:
            m.surface_render_method = "BLENDED"
        except (AttributeError, TypeError):
            pass
        m.use_backface_culling = False
    return m


# ===== 网格构建器 =====
def _newell(pts):
    n = Vector((0, 0, 0))
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


class Mesh:
    """顶点 + 多边形（材质下标、平滑标记）。frame() / place() 之内的点会按变换放置。"""

    def __init__(self):
        self.P = []
        self.F = []
        self._xf = []

    # --- 放置 ---
    @contextmanager
    def place(self, origin=(0, 0, 0), yaw=0.0):
        m = Matrix.Translation(Vector(origin)) @ Matrix.Rotation(yaw, 4, "Z")
        self._xf.append(m)
        try:
            yield self
        finally:
            self._xf.pop()

    @contextmanager
    def frame(self, origin, z_axis, x_hint=(1, 0, 0), spin=0.0):
        """局部 Z 对齐 z_axis、局部原点在 origin；spin 为绕局部 Z 的自转角。"""
        z = Vector(z_axis).normalized()
        xh = Vector(x_hint)
        if abs(xh.normalized().dot(z)) > 0.98:
            xh = Vector((0, 1, 0))
        x = (xh - z * xh.dot(z)).normalized()
        y = z.cross(x)
        r = Matrix(((x.x, y.x, z.x), (x.y, y.y, z.y), (x.z, y.z, z.z))).to_4x4()
        m = Matrix.Translation(Vector(origin)) @ r @ Matrix.Rotation(spin, 4, "Z")
        self._xf.append(m)
        try:
            yield self
        finally:
            self._xf.pop()

    def pt(self, p):
        p = Vector(p)
        for m in reversed(self._xf):
            p = m @ p
        return p

    # --- 顶点 / 面 ---
    def v(self, p):
        self.P.append(self.pt(p))
        return len(self.P) - 1

    def vs(self, pts):
        return [self.v(p) for p in pts]

    def face(self, mat, ids, ref, smooth=False):
        """加一个多边形；ref 为“内部点”（已是世界坐标），法线自动朝外。"""
        ids = list(ids)
        pts = [self.P[i] for i in ids]
        c = sum(pts, Vector((0, 0, 0))) / len(pts)
        if _newell(pts).dot(c - Vector(ref)) < 0:
            ids.reverse()
        self.F.append((mat, ids, smooth))

    def centroid(self, ids):
        return sum((self.P[i] for i in ids), Vector((0, 0, 0))) / len(ids)

    def tris(self):
        return sum(len(i) - 2 for _, i, _ in self.F)

    def used_mats(self):
        return sorted({m for m, _, _ in self.F})

    # --- 放样 ---
    def loft(self, rings, mats, closed=True, smooth=False, ref=None):
        """相邻环两两连成四边形；mats 为按“环边下标”的列表，或 f(段, 边)->材质。"""
        for k in range(len(rings) - 1):
            a, b = rings[k], rings[k + 1]
            n = len(a)
            r = ref if ref is not None else (self.centroid(a) + self.centroid(b)) / 2
            for e in range(n if closed else n - 1):
                e2 = (e + 1) % n
                mat = mats(k, e) if callable(mats) else (mats[e] if isinstance(mats, (list, tuple)) else mats)
                self.face(mat, [a[e], a[e2], b[e2], b[e]], r, smooth)

    def fan(self, ring, apex, mats, smooth=False, ref=None):
        """环收尖到一个顶点（apex 为顶点下标）。"""
        n = len(ring)
        ref = ref if ref is not None else self.centroid(ring)
        for e in range(n):
            mat = mats(e) if callable(mats) else (mats[e] if isinstance(mats, (list, tuple)) else mats)
            self.face(mat, [ring[e], ring[(e + 1) % n], apex], ref, smooth)

    def cap(self, ring, mat, ref, smooth=False):
        self.face(mat, ring, ref, smooth)

    def prism(self, mat, top_pts, bot_pts, smooth=False):
        """同形的上 / 下两组点（凸多边形）围成实心棱柱。"""
        top, bot = self.vs(top_pts), self.vs(bot_pts)
        ref = (self.centroid(top) + self.centroid(bot)) / 2
        self.face(mat, top, ref, smooth)
        self.face(mat, bot, ref, smooth)
        n = len(top)
        for e in range(n):
            self.face(mat, [top[e], top[(e + 1) % n], bot[(e + 1) % n], bot[e]], ref, smooth)
        return top, bot

    def pyramid(self, mat, base_pts, apex, smooth=False, closed=False):
        """棱锥；closed=True 时补底面（需要看得到底面的悬空件）。"""
        base = self.vs(base_pts)
        a = self.v(apex)
        c = self.centroid(base)
        ref = c + (self.P[a] - c) * 0.3
        self.fan(base, a, mat, smooth, ref=ref)
        if closed:
            self.face(mat, base, ref)
        return base, a

    # --- 常用体 ---
    def box(self, mat, c, size, bottom=True, smooth=False):
        """轴对齐长方体（在当前 frame 内）；bottom=False 省掉底面。"""
        cx, cy, cz = c
        hx, hy, hz = (s / 2 for s in size)
        lo = self.vs([(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
                      (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz)])
        hi = self.vs([(cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
                      (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)])
        ref = self.pt(c)
        self.face(mat, hi, ref, smooth)
        if bottom:
            self.face(mat, lo, ref, smooth)
        for e in range(4):
            e2 = (e + 1) % 4
            self.face(mat, [lo[e], lo[e2], hi[e2], hi[e]], ref, smooth)
        return lo, hi

    def lathe(self, profile, sides, mats, rot=0.0, smooth=False, cap_bottom=True, cap_top=True, ellipse=(1.0, 1.0)):
        """绕局部 Z 车削：profile 为 [(r, z)...]（自下而上），r = 0 的端点收成一个点。返回各环下标列表。"""
        rings, apexes = [], {}
        for i, (r, z) in enumerate(profile):
            if r <= 1e-6:
                apexes[i] = self.v((0, 0, z))
                rings.append(None)
            else:
                rings.append(self.vs([(r * ellipse[0] * math.cos(rot + math.tau * k / sides),
                                       r * ellipse[1] * math.sin(rot + math.tau * k / sides), z)
                                      for k in range(sides)]))
        def mat_of(k, e):
            return mats(k, e) if callable(mats) else (mats[e] if isinstance(mats, (list, tuple)) else mats)

        def add(mat, ids):
            self.F.append((mat, ids, smooth))     # 车削面按解析绕序直接加：环逆时针、剖面自下而上 → 法线朝外

        for k in range(len(profile) - 1):
            a, b = rings[k], rings[k + 1]
            if a is None and b is None:
                continue
            for e in range(sides):
                e2 = (e + 1) % sides
                if a is None:                      # 底端收尖
                    add(mat_of(k, e), [b[e2], b[e], apexes[k]])
                elif b is None:                    # 顶端收尖
                    add(mat_of(k, e), [a[e], a[e2], apexes[k + 1]])
                else:
                    add(mat_of(k, e), [a[e], a[e2], b[e2], b[e]])
        if cap_bottom and rings[0] is not None:
            self.F.append((mat_of(0, 0), list(reversed(rings[0])), False))
        if cap_top and rings[-1] is not None:
            self.F.append((mat_of(len(profile) - 2, 0), list(rings[-1]), False))
        return rings

    def rib(self, mat, path, normals, half_w, th, inset=0.55, smooth=False):
        """沿路径的小截面滚边（梯形：贴面两侧 + 外顶），path 为点列、normals 为各点外法线（局部坐标）。
        路径所在的面由调用方保证；截面宽度方向 = normal × 切线。返回各截面环下标。"""
        pts = [Vector(p) for p in path]
        ns = [Vector(n).normalized() for n in normals]
        rings = []
        for i, (p, n) in enumerate(zip(pts, ns)):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            b = n.cross(t).normalized()
            if inset is None:                      # 脊形截面（3 点、两个面）
                rings.append(self.vs([p - b * half_w, p + n * th, p + b * half_w]))
            else:
                rings.append(self.vs([p - b * half_w, p - b * half_w * inset + n * th,
                                      p + b * half_w * inset + n * th, p + b * half_w]))
        for k in range(len(rings) - 1):
            a, bb = rings[k], rings[k + 1]
            ref = self.pt((pts[k] + pts[k + 1]) / 2 - ns[k] * th * 2)
            for e in range(len(a) - 1):
                self.face(mat, [a[e], a[e + 1], bb[e + 1], bb[e]], ref, smooth)
        return rings

    def ribbon(self, mat, path, normals, half_w, lift=0.004):
        """贴面的窄带（单面，浮在曲面上方 lift），给发光电路线用。"""
        pts = [Vector(p) for p in path]
        ns = [Vector(n).normalized() for n in normals]
        rows = []
        for i, (p, n) in enumerate(zip(pts, ns)):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            b = n.cross(t).normalized()
            rows.append(self.vs([p - b * half_w + n * lift, p + b * half_w + n * lift]))
        for k in range(len(rows) - 1):
            ref = self.pt((pts[k] + pts[k + 1]) / 2 - ns[k] * 0.05)
            self.face(mat, [rows[k][0], rows[k][1], rows[k + 1][1], rows[k + 1][0]], ref)
        return rows

    @staticmethod
    def ngon(r, n, z=0.0, rot=0.0, sx=1.0, sy=1.0):
        return [(r * sx * math.cos(rot + math.tau * k / n), r * sy * math.sin(rot + math.tau * k / n), z)
                for k in range(n)]


def make_object(name, mesh, materials, location=(0, 0, 0)):
    """把 Mesh 变成挂在场景里的对象；材质槽只放被用到的材质（按原顺序重映射）。"""
    used = mesh.used_mats()
    remap = {old: new for new, old in enumerate(used)}
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in mesh.P], [], [ids for _, ids, _ in mesh.F])
    for old in used:
        me.materials.append(materials[old])
    for poly, (mi, _ids, smooth) in zip(me.polygons, mesh.F):
        poly.material_index = remap[mi]
        poly.use_smooth = smooth
    me.update()
    me.validate()
    obj = bpy.data.objects.new(name, me)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    return obj


def count_tris(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    me = obj.evaluated_get(depsgraph).data
    return sum(len(p.vertices) - 2 for p in me.polygons)
