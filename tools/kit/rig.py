"""角色工具包 · 骨骼、蒙皮、布料链、姿态 / IK、动作关键帧与 GLB 导出。

姿态约定（与尼克斯相同）：pose[骨名] 是“以静止姿态骨架轴表达的局部旋转”，
子骨的世界增量 = 父骨世界增量 @ 自身局部量；位移通道由 Rig.translate 声明（如 Hover 的上下浮动）。
"""

import math

import bpy
from mathutils import Matrix, Vector

from kit.core import TAU, clamp, frame_from, lerp, link

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
I3 = Matrix.Identity(3)
DEPTH = {1: 0.35, 2: 0.65, 3: 1.0, 4: 1.25, 5: 1.5}   # 骨链逐级累加：根部少转、尖端多转


def depth_w(j, count):
    """骨链第 j 节（1 起）的累加权重：逐节递增、总和固定为 2，节数多时弯曲更平滑。"""
    total = sum(k ** 0.8 for k in range(1, count + 1))
    return 2.0 * j ** 0.8 / total


def R(*pairs):
    """R((轴, 角), ...)：按顺序左乘的旋转矩阵（armature 空间轴）。"""
    m = Matrix.Identity(3)
    for axis, angle in pairs:
        m = Matrix.Rotation(angle, 3, Vector(axis).normalized()) @ m
    return m


def swing(a, b):
    """把单位向量 a 转到 b 的最短旋转。"""
    return Vector(a).rotation_difference(Vector(b)).to_matrix()


class Rig:
    def __init__(self, ctx):
        self.ctx = ctx
        self.root = link(bpy.data.objects.new(ctx.ID, None))
        self.root.empty_display_size = 0.3
        self.data = bpy.data.armatures.new(f"{ctx.title} deform bones")
        self.obj = link(bpy.data.objects.new(f"{ctx.ID}_RIG", self.data), self.root)
        bpy.ops.object.select_all(action="DESELECT")
        self.obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj
        bpy.ops.object.mode_set(mode="EDIT")
        self.garments = []
        self.translate = {}     # 骨名 -> pose 里的键（值为 float 表示 Z 位移，或 Vector）
        self.static = set()     # 不写旋转关键帧的骨（例如由网页端驱动的光环骨）
        self.last_q = {}

    # ----- 骨骼 -----
    def bone(self, name, head, tail, parent=None, roll=None):
        b = self.data.edit_bones.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        if parent:
            b.parent = self.data.edit_bones[parent]
        if roll is not None:
            b.align_roll(Vector(roll))
        return b

    def chain(self, prefix, points, parent, roll=None, start=1):
        """沿点列建一条骨链：prefix1、prefix2……首骨挂在 parent 上。"""
        names = []
        for j in range(1, len(points)):
            name = f"{prefix}{j + start - 1}"
            r = roll(j) if callable(roll) else roll
            self.bone(name, points[j - 1], points[j], parent if j == 1 else names[-1], r)
            names.append(name)
        return names

    def add_garment(self, g):
        """为布料 g 建 g.K 条骨链（名字 g.prefix{k}.{j}），挂在 g.parent 上。"""
        self.garments.append(g)
        for k in range(g.K):
            pts = g.chain_points(k)
            for j in range(1, len(pts)):
                radial_dir = g.roll_dir(k, pts[j])
                self.bone(f"{g.prefix}{k}.{j}", pts[j - 1], pts[j],
                          g.parent if j == 1 else f"{g.prefix}{k}.{j - 1}", radial_dir)

    def done(self):
        bpy.ops.object.mode_set(mode="OBJECT")
        bones = self.data.bones
        self.SEG = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in bones}
        self.REST = {b.name: b.matrix_local.to_3x3() for b in bones}
        self.PARENT = {b.name: (b.parent.name if b.parent else None) for b in bones}
        self.LEN = {n: (t - h).length for n, (h, t) in self.SEG.items()}
        return self

    # ----- 蒙皮权重 -----
    def chain_weights(self, p, bones, parent=None, win=0.05):
        """沿骨链投影；关节两侧 win 米内线性混合，首骨根部可混合父骨。"""
        best, bd, bt = 0, 1e9, 0.0
        for i, name in enumerate(bones):
            a, b = self.SEG[name]
            ab = b - a
            t = (p - a).dot(ab) / max(ab.length_squared, 1e-9)
            d = (p - a.lerp(b, clamp(t))).length
            if d < bd:
                best, bd, bt = i, d, t
        a, b = self.SEG[bones[best]]
        length = (b - a).length
        w = {bones[best]: 1.0}
        lead, tail = bt * length, (1 - bt) * length
        if lead < win:
            blend = clamp(0.5 * (1 - lead / win), 0, 1)
            prev = bones[best - 1] if best > 0 else parent
            if prev:
                w[prev] = blend
                w[bones[best]] -= blend
        if tail < win and best < len(bones) - 1:
            blend = 0.5 * (1 - tail / win)
            w[bones[best + 1]] = blend
            w[bones[best]] -= blend
        return w

    @staticmethod
    def band_weights(z, levels):
        if z >= levels[0][0]:
            return {levels[0][1]: 1.0}
        for (z0, b0), (z1, b1) in zip(levels, levels[1:]):
            if z >= z1:
                t = (z - z1) / max(1e-6, z0 - z1)
                return {b0: t, b1: 1 - t} if b0 != b1 else {b0: 1.0}
        return {levels[-1][1]: 1.0}

    def weights_for(self, spec, p):
        kind = spec[0]
        if kind == "rigid":
            return spec[1]
        if kind == "chain":
            return self.chain_weights(p, spec[1], spec[2], spec[3])
        if kind == "bands":
            return self.band_weights(p.z, spec[1])
        if kind == "garment":
            g = spec[1]
            return g.weights(*g.param(p))
        if kind == "fn":
            return spec[1](p)
        raise ValueError(kind)

    def bind(self):
        for obj, spec in self.ctx.parts:
            groups = {}
            mw = obj.matrix_world
            for vert in obj.data.vertices:
                for name, w in self.weights_for(spec, mw @ vert.co).items():
                    if w <= 1e-4:
                        continue
                    if name not in groups:
                        groups[name] = obj.vertex_groups.new(name=name)
                    groups[name].add([vert.index], w, "ADD")
            mod = obj.modifiers.new("Skeletal deformation", "ARMATURE")
            mod.object = self.obj
            obj.parent = self.obj
        self._merge_skinned()
        self._attach()

    def _merge_skinned(self):
        by_mat = {}
        for obj, _ in self.ctx.parts:
            by_mat.setdefault(obj.data.materials[0].name, []).append(obj)
        self.meshes = []
        for name, objs in by_mat.items():
            bpy.ops.object.select_all(action="DESELECT")
            for o in objs:
                o.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]
            if len(objs) > 1:
                bpy.ops.object.join()
            objs[0].name = f"{self.ctx.ID} | {name}"
            self.meshes.append(objs[0])

    def _attach(self):
        """挂骨件按（骨，首材质）合并后刚性挂到骨上，保持世界位置。"""
        groups = {}
        for obj, bone, keep in self.ctx.attached:
            key = (bone, obj.name) if keep else (bone, obj.data.materials[0].name if obj.data.materials else "")
            groups.setdefault(key, []).append((obj, keep))
        self.attached = []
        for (bone, mname), items in groups.items():
            objs = [o for o, _ in items]
            bpy.ops.object.select_all(action="DESELECT")
            for o in objs:
                o.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]
            if len(objs) > 1:
                bpy.ops.object.join()
            obj = objs[0]
            if not items[0][1]:
                obj.name = f"{self.ctx.ID} @ {bone} | {mname}"
            bpy.context.view_layer.update()
            world = obj.matrix_world.copy()
            obj.parent = self.obj
            obj.parent_type = "BONE"
            obj.parent_bone = bone
            bpy.context.view_layer.update()
            obj.matrix_world = world
            self.attached.append(obj)

    # ----- 姿态运算 -----
    def delta(self, pose, name, cache=None):
        cache = {} if cache is None else cache
        if name in cache:
            return cache[name]
        w = pose.get(name, I3)
        par = self.PARENT[name]
        d = (self.delta(pose, par, cache) @ w) if par else w
        cache[name] = d
        return d

    def offset(self, pose, name):
        key = self.translate.get(name)
        if key is None:
            return Vector((0, 0, 0))
        val = pose.get(key, 0.0)
        return Vector((0, 0, val)) if isinstance(val, (int, float)) else Vector(val)

    def head(self, pose, name, cache=None):
        """姿态下骨头部在 armature 空间的位置。"""
        par = self.PARENT[name]
        h = self.SEG[name][0]
        if not par:
            return h + self.offset(pose, name)
        ph = self.head(pose, par, cache)
        return ph + self.delta(pose, par, cache) @ (h - self.SEG[par][0]) + self.offset(pose, name)

    def tail(self, pose, name, cache=None):
        h, t = self.SEG[name]
        return self.head(pose, name, cache) + self.delta(pose, name, cache) @ (t - h)

    def aim(self, pose, name, direction, up=None, rest_up=None, cache=None):
        """让骨 name 指向 direction（armature 空间）；给 up/rest_up 时同时控制滚转。"""
        h, t = self.SEG[name]
        rest_dir = (t - h).normalized()
        if up is None:
            d = swing(rest_dir, Vector(direction).normalized())
        else:
            f_rest = frame_from(rest_dir, rest_up if rest_up is not None else up)
            f_new = frame_from(direction, up)
            d = f_new @ f_rest.transposed()
        par = self.PARENT[name]
        cache = {} if cache is None else cache
        pd = self.delta(pose, par, cache) if par else I3
        pose[name] = pd.inverted() @ d
        cache.pop(name, None)
        return d

    def ik2(self, pose, upper, lower, target, pole, end=None, end_dir=None, end_up=Z, rest_pole=Y):
        """两段式 IK：upper/lower 两骨末端到达 target，膝 / 肘朝 pole 方向；end 为末端骨（脚）。"""
        cache = {}
        hip = self.head(pose, upper, cache)
        a, b = self.LEN[upper], self.LEN[lower]
        d = Vector(target) - hip
        dist = clamp(d.length, 1e-4, (a + b) * 0.9995)
        dn = d.normalized()
        cos_a = clamp((a * a + dist * dist - b * b) / (2 * a * dist), -1, 1)
        pv = Vector(pole)
        perp = pv - dn * pv.dot(dn)
        perp = perp.normalized() if perp.length > 1e-6 else Y
        upper_dir = dn * cos_a + perp * math.sqrt(max(0.0, 1 - cos_a * cos_a))
        knee = hip + upper_dir * a
        lower_dir = (hip + dn * dist - knee).normalized()
        self.aim(pose, upper, upper_dir, up=perp, rest_up=rest_pole, cache=cache)
        cache = {}
        self.aim(pose, lower, lower_dir, up=perp, rest_up=rest_pole, cache=cache)
        if end and end_dir is not None:
            self.aim(pose, end, end_dir, up=end_up, rest_up=Z, cache={})
        return knee

    def garment_pose(self, pose, g, flare, side=None, extra=None):
        """布料链摆动：flare(k, j) 为向外掀起的角，side(k, j) 为侧摆，按骨链深度累加。"""
        for k in range(g.K):
            tang, rad = g.axes(k, self.SEG)
            for j in range(1, g.J + 1):
                dep = depth_w(j, g.J)
                m = R((tang, flare(k, j) * dep))
                if side:
                    m = R((rad, side(k, j) * dep)) @ m
                if extra:
                    m = extra(k, j) @ m
                pose[f"{g.prefix}{k}.{j}"] = m

    def wind(self, pose, g, back, flare=None, side=None):
        """风压：所有布料链统一向身后（-Y）飘 back(k, j) 弧度，可叠加少量径向鼓起 flare 与侧摆 side。
        奔跑角色的披风用它，避免两侧链条各自向外掀成硬板。"""
        for k in range(g.K):
            tang, rad = g.axes(k, self.SEG)
            for j in range(1, g.J + 1):
                dep = depth_w(j, g.J)
                m = R((X, -back(k, j) * dep))
                if flare:
                    m = m @ R((tang, flare(k, j) * dep))
                if side:
                    m = R((Z, side(k, j) * dep)) @ m
                pose[f"{g.prefix}{k}.{j}"] = m

    # ----- 动作 -----
    def put_pose(self, pose, frame):
        for pb in self.obj.pose.bones:
            if pb.name in self.static:
                continue
            pb.rotation_mode = "QUATERNION"
            rest = self.REST[pb.name]
            q = (rest.inverted() @ pose.get(pb.name, I3) @ rest).to_quaternion()
            prev = self.last_q.get(pb.name)
            if (prev is not None and q.dot(prev) < 0) or (prev is None and q.w < 0):
                q.negate()        # q 与 -q 等价，分量插值却会绕远路，造成中间帧翻转
            self.last_q[pb.name] = q.copy()
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
        for name in self.translate:
            pb = self.obj.pose.bones[name]
            pb.location = self.REST[name].inverted() @ self.offset(pose, name)
            pb.keyframe_insert("location", frame=frame, group=name)

    def new_action(self, name):
        self.last_q.clear()
        act = bpy.data.actions.new(name)
        act.use_fake_user = True   # 未挂骨架的动作没有使用者，不设 fake user 会在保存 .blend 时丢失
        self.obj.animation_data_create()
        self.obj.animation_data.action = act
        return act

    def loop(self, name, frames, pose_fn, step=2):
        """循环动作：pose_fn(t) 的 t 从 0 走到 2π，首尾同相位。"""
        self.new_action(name)
        for f in range(0, frames + 1, step):
            self.put_pose(pose_fn(TAU * f / frames), f + 1)

    def keyed(self, name, keys):
        """关键姿态动作：keys 为 [(帧, 姿态), ...]。"""
        self.new_action(name)
        for frame, pose in keys:
            self.put_pose(pose, frame)

    def sampled(self, name, frames, pose_fn, step=1):
        """逐帧采样的一次性动作：pose_fn(s) 的 s 从 0 到 1。"""
        self.new_action(name)
        for f in range(0, frames + 1, step):
            self.put_pose(pose_fn(f / frames), f + 1)

    def motion_check(self, names):
        """每段动作里布料末端骨相对静止方向的最大偏转角，防止飘带翻成“翅膀”。"""
        scene = bpy.context.scene
        tips = {f"{g.prefix}{k}.{g.J}" for g in self.garments for k in range(g.K)}
        for act_name in names:
            self.obj.animation_data.action = bpy.data.actions[act_name]
            first, last = map(int, bpy.data.actions[act_name].frame_range)
            worst = (0.0, "", 0)
            for f in range(first, last + 1, 2):
                scene.frame_set(f)
                for pb in self.obj.pose.bones:
                    if pb.name not in tips:
                        continue
                    h, t = self.SEG[pb.name]
                    ang = math.degrees((t - h).normalized().angle((pb.tail - pb.head).normalized(), 0))
                    if ang > worst[0]:
                        worst = (ang, pb.name, f)
            print(f"MOTION CHECK {act_name}: max tail swing {worst[0]:.1f} deg at {worst[1]} frame {worst[2]}")
        self.obj.animation_data.action = bpy.data.actions[names[0]]
        scene.frame_set(1)

    # ----- 导出 -----
    def save_blend(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        for image in bpy.data.images:
            if image.source == "FILE" and not image.packed_file:
                image.pack()
        bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
        print("SAVED", path)

    def _select_all(self, skip=()):
        bpy.ops.object.select_all(action="DESELECT")
        for obj in [self.root, *self.root.children_recursive]:
            if obj not in skip:
                obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj

    def _export(self, path, quality, skip=()):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._select_all(skip)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                                  export_apply=True, export_animation_mode="ACTIONS",
                                  export_image_format="WEBP", export_image_quality=quality)

    def tris(self):
        dg = bpy.context.evaluated_depsgraph_get()
        return sum(sum(len(p.vertices) - 2 for p in o.evaluated_get(dg).data.polygons)
                   for o in self.root.children_recursive if o.type == "MESH" and o not in self.ctx.hidden)

    def export(self, full_out, game_out, target=60000, keep=("inlay", "glow", "hem", "trim", "core"),
               min_ratio=0.12, tex_half=True, min_mesh=3000):
        """导出展示版高模，再按三角面预算自动减面（keep 关键字的材质网格不动）导出游戏版。"""
        self._export(full_out, 88)
        full = self.tris()
        print("EXPORTED", full_out, full_out.stat().st_size, "TRIS", full)
        dg = bpy.context.evaluated_depsgraph_get()
        meshes = [o for o in self.root.children_recursive if o.type == "MESH" and o not in self.ctx.hidden]
        count = {o: sum(len(p.vertices) - 2 for p in o.evaluated_get(dg).data.polygons) for o in meshes}
        big = [o for o in meshes if count[o] > min_mesh and not any(k in o.name.lower() for k in keep)]
        fixed = sum(count[o] for o in meshes if o not in big)
        big_sum = sum(count[o] for o in big)
        if big and fixed + big_sum > target:
            ratio = clamp((target - fixed) / big_sum, min_ratio, 1.0)
            for o in big:
                mod = o.modifiers.new("Game LOD", "DECIMATE")
                mod.ratio = ratio
                o.modifiers.move(len(o.modifiers) - 1, 0)
            print("GAME LOD ratio", round(ratio, 3), "on", len(big), "meshes")
        if tex_half:
            for image in bpy.data.images:
                if image.size[0] >= 512:
                    image.scale(image.size[0] // 2, image.size[1] // 2)
        self._export(game_out, 85, skip=set(self.ctx.hidden))
        print("EXPORTED", game_out, game_out.stat().st_size, "TRIS", self.tris())
