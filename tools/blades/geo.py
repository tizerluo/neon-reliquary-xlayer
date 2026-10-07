"""飞剑游戏版 · 低面数几何构建器。

纯 Python 顶点 / 面表 → Blender 网格。坐标约定（Blender，Z 向上，导出 glTF 后 Y 向上）：
剑尖指向 +X，剑身平躺在 XY 平面（宽面朝 +Z，厚度方向 Z），原点在护手中心。
法线统一在建面时按“内部参考点”定向，不依赖 bmesh 重算。
"""

import math
from contextlib import contextmanager

import bpy
from mathutils import Matrix, Vector


# ===== 颜色 =====
def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(hexcolor):
    """#rrggbb（sRGB）→ 线性 RGB 三元组（Principled / glTF 因子用线性值）。"""
    h = hexcolor.lstrip("#")
    return tuple(_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def make_material(name, base, metal=0.0, rough=0.5, emit=None, strength=0.0, spec=0.5):
    """纯色 Principled 材质；base / emit 为 #rrggbb。无贴图、无顶点色。"""
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
    if emit:
        put("Emission Color", (*lin(emit), 1))
        put("Emission Strength", strength)
    else:
        put("Emission Strength", 0.0)
    m.diffuse_color = (*lin(base), 1)
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
    """顶点 + 多边形（材质下标、平滑标记）。place() 之内的点会按偏移 / 偏航旋转放置。"""

    def __init__(self):
        self.P = []
        self.F = []
        self._xf = [(Vector((0, 0, 0)), 0.0)]

    # --- 放置 ---
    @contextmanager
    def place(self, origin=(0, 0, 0), yaw=0.0):
        self._xf.append((Vector(origin), yaw))
        try:
            yield self
        finally:
            self._xf.pop()

    def pt(self, p):
        p = Vector(p)
        for o, yaw in reversed(self._xf):
            if yaw:
                p = Matrix.Rotation(yaw, 3, "Z") @ p
            p = p + o
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
    def loft(self, rings, mats, closed=True, smooth=False):
        """相邻环两两连成四边形；mats 为按“环边下标”的列表，或 f(段, 边)->材质。"""
        for k in range(len(rings) - 1):
            a, b = rings[k], rings[k + 1]
            n = len(a)
            ref = (self.centroid(a) + self.centroid(b)) / 2
            for e in range(n if closed else n - 1):
                e2 = (e + 1) % n
                mat = mats(k, e) if callable(mats) else (mats[e] if isinstance(mats, (list, tuple)) else mats)
                self.face(mat, [a[e], a[e2], b[e2], b[e]], ref, smooth)

    def fan(self, ring, apex, mats, smooth=False, ref=None):
        """环收尖到一个顶点（apex 为顶点下标）。"""
        n = len(ring)
        ref = ref if ref is not None else self.centroid(ring)
        for e in range(n):
            mat = mats(e) if callable(mats) else (mats[e] if isinstance(mats, (list, tuple)) else mats)
            self.face(mat, [ring[e], ring[(e + 1) % n], apex], ref, smooth)

    def cap(self, ring, mat, ref, smooth=False):
        self.face(mat, ring, ref, smooth)

    def prism(self, mat, tri_top, tri_bot, smooth=False):
        """用同形的上 / 下两组点（≥3）围成实心棱柱（凸多边形）。"""
        top, bot = self.vs(tri_top), self.vs(tri_bot)
        ref = (self.centroid(top) + self.centroid(bot)) / 2
        self.face(mat, top, ref, smooth)
        self.face(mat, bot, ref, smooth)
        n = len(top)
        for e in range(n):
            self.face(mat, [top[e], top[(e + 1) % n], bot[(e + 1) % n], bot[e]], ref, smooth)
        return top, bot

    def pyramid(self, mat, base_pts, apex, smooth=False):
        """无底棱锥（底面埋在别的几何里）。"""
        base = self.vs(base_pts)
        a = self.v(apex)
        c = self.centroid(base)
        self.fan(base, a, mat, smooth, ref=c + (self.P[a] - c) * 0.3)
        return base, a

    # --- 常用截面 ---
    @staticmethod
    def polygon_yz(x, r, sides=6, ry=None, rz=None, rot=0.0):
        """YZ 平面内的正多边形环（轴沿 X），返回点列。"""
        ry = r if ry is None else ry
        rz = r if rz is None else rz
        return [(x, ry * math.cos(rot + math.tau * k / sides), rz * math.sin(rot + math.tau * k / sides))
                for k in range(sides)]


def make_object(name, mesh, materials):
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
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def count_tris(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    me = obj.evaluated_get(depsgraph).data
    return sum(len(p.vertices) - 2 for p in me.polygons)
