"""构建 NYX · 虚空工匠：悬浮幽影角色的网格、骨骼、蒙皮、动作与 GLB。

在仓库根目录运行：
    blender --background --python tools/build_nyx.py
产物：visual-lab/assets/nyx-void-artificer.glb、art/nyx-void-artificer.blend
设置环境变量 NYX_STAGE=geo 时只建几何并保存 .blend，便于快速审图。
"""

import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nyx_body as body  # noqa: E402
from nyx_lib import ROOT, TAU, clamp, link  # noqa: E402

OUT = ROOT / "visual-lab" / "assets" / "nyx-void-artificer.glb"
GAME_OUT = ROOT / "visual-lab" / "assets" / "nyx-void-artificer-game.glb"
BLEND = ROOT / "art" / "nyx-void-artificer.blend"
# 游戏内 LOD 的减面比例（按材质网格名匹配），未列出的小件保持原样，细管状光缝不会被塌陷
GAME_LOD = {"obsidian": 0.10, "velvet": 0.18, "platinum": 0.30, "glass mask": 0.40, "bodysuit": 0.45}
FPS = 24
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
SKIRT_K, CAPE_K = 8, 5
SKIRT_J, CAPE_J, TABARD_J = (0, 0.30, 0.62, 1.0), (0, 0.28, 0.60, 1.0), (0, 0.30, 0.62, 1.0)
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
M = body.make_materials()
halo, needle = body.build_all(M)
root = link(bpy.data.objects.new("NYX", None))
root.empty_display_size = 0.3


def save_blend():
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    for image in bpy.data.images:
        if image.source == "FILE" and not image.packed_file:
            image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    print("SAVED", BLEND)


if os.environ.get("NYX_STAGE") == "geo":
    for obj, _ in body.PARTS:
        obj.parent = root
    halo.parent = root
    needle.parent = root
    save_blend()
    raise SystemExit(0)

# ===== 骨骼 =====
arm_data = bpy.data.armatures.new("Nyx deform bones")
rig = link(bpy.data.objects.new("NYX_RIG", arm_data), root)
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")


def bone(name, head, tail, parent=None, roll=None):
    b = arm_data.edit_bones.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    if parent:
        b.parent = arm_data.edit_bones[parent]
    if roll is not None:
        b.align_roll(Vector(roll))
    return b


def inset(p, d=0.012):
    return p - Vector((p.x, p.y, 0)).normalized() * d


bone("Root", (0, 0, 0), (0, 0, 0.2))
bone("Hover", (0, 0, 0.2), (0, 0, 0.45), "Root")
bone("Pelvis", (0, 0, 1.22), (0, 0, 1.40), "Hover", roll=Y)
bone("Spine", (0, 0, 1.40), (0, 0, 1.56), "Pelvis", roll=Y)
bone("Chest", (0, 0, 1.56), (0, 0, 1.77), "Spine", roll=Y)
bone("Neck", (0, 0.004, 1.78), (0, 0.010, 1.90), "Chest", roll=Y)
bone("Head", (0, 0.010, 1.90), (0, 0.010, 2.12), "Neck", roll=Y)
bone("Halo", body.HALO_C, body.HALO_C + Vector((0, -0.15, 0)), "Chest", roll=Z)
for label in ("L", "R"):
    a, h = body.ARMS[label], body.HANDS[label]
    bone(f"UpperArm.{label}", a["shoulder"], a["elbow"], "Chest", roll=Y)
    bone(f"Forearm.{label}", a["elbow"], a["wrist"], f"UpperArm.{label}", roll=Y)
    bone(f"Hand.{label}", h["wrist"], h["knuckle"], f"Forearm.{label}", roll=h["n"])
    for name, (base, tip) in h["fingers"].items():
        bone(f"{name}.{label}", base, tip, f"Hand.{label}", roll=h["n"])


def chain_bones(prefix, count, joints_v, point_fn, parent):
    for k in range(count):
        u = (k + 0.5) / count
        pts = [inset(point_fn(u, v)) for v in joints_v]
        for j in range(1, len(pts)):
            radial = Vector((pts[j].x, pts[j].y, 0)).normalized()
            bone(f"{prefix}{k}.{j}", pts[j - 1], pts[j], parent if j == 1 else f"{prefix}{k}.{j - 1}", roll=radial)


chain_bones("Skirt", SKIRT_K, SKIRT_J, body.skirt_point, "Pelvis")
chain_bones("Cape", CAPE_K, CAPE_J, body.cape_point, "Chest")
tab = [body.tabard_point(0.5, v) - Vector((0, 0.01, 0)) for v in TABARD_J]
for j in range(1, 4):
    bone(f"Tabard.{j}", tab[j - 1], tab[j], "Pelvis" if j == 1 else f"Tabard.{j - 1}", roll=Y)
bpy.ops.object.mode_set(mode="OBJECT")

SEG = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm_data.bones}
REST = {b.name: b.matrix_local.to_3x3() for b in arm_data.bones}


# ===== 蒙皮权重 =====
def closest_t(p, a, b):
    ab = b - a
    return (p - a).dot(ab) / max(ab.length_squared, 1e-9)


def chain_weights(p, bones, parent=None, win=0.05):
    """沿骨链投影；关节两侧 win 米内线性混合，首骨根部可混合父骨。"""
    best, bd, bt = 0, 1e9, 0.0
    for i, name in enumerate(bones):
        a, b = SEG[name]
        t = closest_t(p, a, b)
        d = (p - a.lerp(b, clamp(t))).length
        if d < bd:
            best, bd, bt = i, d, t
    a, b = SEG[bones[best]]
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


def chain_v(v, bones, parent, joints, top_win, win=0.07):
    s = max(i for i in range(len(bones)) if v >= joints[i] - 1e-9)
    w = {bones[s]: 1.0}
    if s == 0 and v < top_win:
        pw = 1 - v / top_win
        w = {parent: pw, bones[0]: 1 - pw}
    elif s > 0 and v - joints[s] < win:
        t = 0.5 * (1 - (v - joints[s]) / win)
        w[bones[s - 1]] = t
        w[bones[s]] -= t
    if s < len(bones) - 1 and joints[s + 1] - v < win:
        t = 0.5 * (1 - (joints[s + 1] - v) / win)
        w[bones[s + 1]] = w.get(bones[s + 1], 0) + t
        w[bones[s]] -= t
    return w


def garment_weights(u, v, prefix, count, parent, joints, top_win):
    x = u * count - 0.5
    k0 = math.floor(x)
    f = x - k0
    if k0 < 0:
        mix = [(0, 1.0)]
    elif k0 >= count - 1:
        mix = [(count - 1, 1.0)]
    else:
        mix = [(k0, 1 - f), (k0 + 1, f)]
    out = {}
    for k, cw in mix:
        names = [f"{prefix}{k}.{j}" for j in range(1, 4)]
        for name, w in chain_v(v, names, parent, joints, top_win).items():
            out[name] = out.get(name, 0) + w * cw
    return out


def hood_weights(p):
    z = p.z
    if z >= 1.90:
        return {"Head": 1.0}
    if z >= 1.84:
        t = (z - 1.84) / 0.06
        return {"Head": t, "Neck": 1 - t}
    if z >= 1.78:
        t = (z - 1.78) / 0.06
        return {"Neck": t, "Chest": 1 - t}
    return {"Chest": 1.0}


def weights_for(spec, p):
    kind = spec[0]
    if kind == "rigid":
        return spec[1]
    if kind == "invdist":
        return chain_weights(p, spec[1], None, 0.05)
    if kind == "chain":
        return chain_weights(p, spec[1], spec[2], spec[3])
    if kind == "finger":
        return chain_weights(p, [f"{spec[2]}.{spec[1]}"], f"Hand.{spec[1]}", 0.012)
    if kind == "hood":
        return hood_weights(p)
    if kind == "skirt":
        u, v = body.skirt_param(p)
        return garment_weights(u, v, "Skirt", SKIRT_K, "Pelvis", SKIRT_J, 0.14)
    if kind == "cape":
        u, v = body.cape_param(p)
        return garment_weights(u, v, "Cape", CAPE_K, "Chest", CAPE_J, 0.12)
    if kind == "tabard":
        v = clamp((body.TABARD_TOP - p.z) / (body.TABARD_TOP - body.TABARD_TIP))
        return chain_v(v, ["Tabard.1", "Tabard.2", "Tabard.3"], "Pelvis", TABARD_J, 0.12)
    raise ValueError(kind)


for obj, spec in body.PARTS:
    groups = {}
    for vert in obj.data.vertices:
        for name, w in weights_for(spec, obj.matrix_world @ vert.co).items():
            if w <= 1e-4:
                continue
            if name not in groups:
                groups[name] = obj.vertex_groups.new(name=name)
            groups[name].add([vert.index], w, "ADD")
    mod = obj.modifiers.new("Nyx skeletal deformation", "ARMATURE")
    mod.object = rig
    obj.parent = rig

# 按首个材质合并网格，减少浏览器端节点与绘制批次
by_mat = {}
for obj, _ in body.PARTS:
    by_mat.setdefault(obj.data.materials[0].name, []).append(obj)
for name, objs in by_mat.items():
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = f"NYX | {name}"

# 光环挂在 Halo 骨上（不蒙皮，网页端绕环法线旋转）；针刃挂在根节点，由网页克隆
bpy.context.view_layer.update()
world = halo.matrix_world.copy()
halo.parent = rig
halo.parent_type = "BONE"
halo.parent_bone = "Halo"
bpy.context.view_layer.update()
halo.matrix_world = world
needle.parent = root


# ===== 动作 =====
def R(*pairs):
    m = Matrix.Identity(3)
    for axis, angle in pairs:
        m = Matrix.Rotation(angle, 3, Vector(axis).normalized()) @ m
    return m


def radial_axes(prefix, k, count):
    """返回链 k 的切向轴（正角外摆）与径向轴（侧摆）。"""
    a0, a1 = SEG[f"{prefix}{k}.1"]
    r = Vector((a1.x, a1.y, 0)).normalized()
    return Vector((r.y, -r.x, 0)), r


LAST_Q = {}   # 每段动作内逐骨记录上一帧四元数，保证符号连续


def put_pose(pose, frame):
    for pb in rig.pose.bones:
        if pb.name == "Halo":
            continue
        pb.rotation_mode = "QUATERNION"
        world = pose.get(pb.name, Matrix.Identity(3))
        rest = REST[pb.name]
        q = (rest.inverted() @ world @ rest).to_quaternion()
        prev = LAST_Q.get(pb.name)
        if (prev is not None and q.dot(prev) < 0) or (prev is None and q.w < 0):
            q.negate()        # q 与 -q 等价，但分量插值会绕远路，造成中间帧翻转
        LAST_Q[pb.name] = q.copy()
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
    hover = rig.pose.bones["Hover"]
    hover.location = REST["Hover"].inverted() @ Vector((0, 0, pose.get("_hover", 0.0)))
    hover.keyframe_insert("location", frame=frame, group="Hover")


DEPTH = {1: 0.35, 2: 0.65, 3: 1.0}   # 骨链逐级累加，根部少转、尖端多转


def garments(pose, t, skirt_flare, skirt_side, cape_flare, cape_side, tabard_swing):
    for k in range(SKIRT_K):
        tang, rad = radial_axes("Skirt", k, SKIRT_K)
        for j in range(1, 4):
            d = DEPTH[j]
            pose[f"Skirt{k}.{j}"] = R((tang, skirt_flare(k, j) * d), (rad, skirt_side(k, j) * d))
    for k in range(CAPE_K):
        tang, rad = radial_axes("Cape", k, CAPE_K)
        for j in range(1, 4):
            d = DEPTH[j]
            pose[f"Cape{k}.{j}"] = R((tang, cape_flare(k, j) * d), (rad, cape_side(k, j) * d))
    for j in range(1, 4):
        pose[f"Tabard.{j}"] = R((X, tabard_swing(j) * DEPTH[j]))


def fingers(pose, label, curl):
    h = body.HANDS[label]
    axis = h["f"].cross(h["n"])
    for i, name in enumerate(FINGERS):
        pose[f"{name}.{label}"] = R((axis, curl(i)))


def idle_pose(t):
    s = math.sin
    p = {"_hover": 0.035 * s(t)}
    p["Pelvis"] = R((X, 0.02 * s(t + 0.6)))
    p["Spine"] = R((X, -0.015 * s(t + 1.0)))
    p["Chest"] = R((X, -0.02 * s(t + 1.3)), (Y, 0.012 * s(t)))
    p["Neck"] = R((X, 0.015 * s(t + 2.0)))
    p["Head"] = R((X, 0.03 * s(t + 2.2)), (Z, 0.05 * s(t)))
    for label, sg in (("L", -1), ("R", 1)):
        p[f"UpperArm.{label}"] = R((Y, sg * 0.045 * s(t + 0.5 * sg)), (X, 0.03 * s(t + 1)))
        p[f"Forearm.{label}"] = R((X, 0.05 * s(t + 1.4)))
        p[f"Hand.{label}"] = R((X, 0.07 * s(2 * t + 0.3 * sg)))
        fingers(p, label, lambda i: 0.10 + 0.08 * s(2 * t + i * 0.6))
    garments(p, t,
             lambda k, j: 0.03 + 0.045 * s(t + k * 0.8 + j * 0.9),
             lambda k, j: 0.04 * s(2 * t + k * 1.1 + j * 0.7),
             lambda k, j: 0.02 + 0.05 * s(t + j * 0.8 + k * 0.5),
             lambda k, j: 0.035 * s(t + k * 0.9 + j * 0.6),
             lambda j: -0.03 * s(t + j * 0.8))
    return p


def drift_pose(t):
    s = math.sin
    p = {"_hover": 0.02 * s(2 * t)}
    p["Pelvis"] = R((X, -0.16 + 0.015 * s(2 * t)))
    p["Spine"] = R((X, -0.05))
    p["Chest"] = R((X, -0.04), (Y, 0.02 * s(t)))
    p["Head"] = R((X, 0.16))
    for label, sg in (("L", -1), ("R", 1)):
        p[f"UpperArm.{label}"] = R((Y, sg * -0.25), (X, -0.55 + 0.04 * s(2 * t + sg)))
        p[f"Forearm.{label}"] = R((X, -0.25))
        p[f"Hand.{label}"] = R((X, -0.30 + 0.06 * s(4 * t + sg)))
        fingers(p, label, lambda i: 0.05)
    garments(p, t,
             lambda k, j: 0.04 + 0.07 * s(4 * t + k * 0.9 + j * 1.2),
             lambda k, j: 0.05 * s(2 * t + k * 1.3 + j),
             lambda k, j: 0.18 + 0.08 * s(4 * t + k * 0.7 + j * 1.1),
             lambda k, j: 0.05 * s(2 * t + k + j * 0.8),
             lambda j: -0.16 + 0.06 * s(4 * t + j))
    for k in range(SKIRT_K):                      # 整体被“风”压向身后
        for j in range(1, 4):
            p[f"Skirt{k}.{j}"] = R((X, -0.12 * DEPTH[j])) @ p[f"Skirt{k}.{j}"]
    return p


def cast_key(stage):
    """stage：0 起势、1 蓄力、2 推掌、3 定格。"""
    p = idle_pose(0)
    if stage == 0:
        return p
    windup = stage == 1
    p["_hover"] = 0.0 if windup else 0.03
    p["Spine"] = R((X, 0.06 if windup else -0.10))
    p["Pelvis"] = R((X, 0.0 if windup else -0.05))
    p["Chest"] = R((Z, 0.28 if windup else -0.22))
    if windup:
        p["UpperArm.R"] = R((X, -0.50), (Y, 0.15))
        p["Forearm.R"] = R((X, 0.60))
        p["UpperArm.L"] = R((X, 0.40))
        p["Hand.R"] = R((X, 0.3))
        fingers(p, "R", lambda i: 0.35)
    else:
        overshoot = 1.08 if stage == 2 else 1.0
        p["UpperArm.R"] = R((X, 1.05 * overshoot), (Y, -0.35))
        p["Forearm.R"] = R((X, -0.10))
        p["Hand.R"] = R((X, -0.60))
        p["UpperArm.L"] = R((X, 0.75 * overshoot), (Y, 0.35))
        p["Forearm.L"] = R((X, -0.05))
        p["Hand.L"] = R((X, -0.45))
        fingers(p, "R", lambda i: -0.15)
        fingers(p, "L", lambda i: -0.12)
        garments(p, 0, lambda k, j: 0.10, lambda k, j: 0.0,
                 lambda k, j: 0.16, lambda k, j: 0.0, lambda j: -0.14)
    return p


def channel_key(stage):
    p = idle_pose(0)
    if stage == 0:
        return p
    p["_hover"] = 0.12
    p["Head"] = R((X, 0.18))
    p["Chest"] = R((X, 0.08))
    for label, sg in (("L", -1), ("R", 1)):
        p[f"UpperArm.{label}"] = R((Y, sg * -0.85), (X, 0.25))
        p[f"Forearm.{label}"] = R((X, 0.35))
        p[f"Hand.{label}"] = R((X, -0.40))
        fingers(p, label, lambda i: -0.12)
    garments(p, 0, lambda k, j: 0.16, lambda k, j: 0.0,
             lambda k, j: 0.18, lambda k, j: 0.0, lambda j: -0.10)
    return p


def new_action(name):
    LAST_Q.clear()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True   # 未挂在骨架上的动作没有使用者，不设 fake user 会在保存 .blend 时被丢弃
    rig.animation_data_create()
    rig.animation_data.action = act
    return act


def loop_action(name, frames, pose_fn, step=2):
    new_action(name)
    for f in range(0, frames + 1, step):
        put_pose(pose_fn(TAU * f / frames), f + 1)


def keyed_action(name, keys):
    new_action(name)
    for frame, pose in keys:
        put_pose(pose, frame)


loop_action("Idle", 72, idle_pose)
loop_action("Drift", 48, drift_pose)
keyed_action("Cast", [(1, cast_key(0)), (8, cast_key(1)), (14, cast_key(2)), (20, cast_key(3)),
                      (32, cast_key(0))])
keyed_action("Channel", [(1, channel_key(0)), (13, channel_key(1)), (28, channel_key(1)),
                         (42, channel_key(0))])
# 自检：每段动作里布料末端骨相对静止姿态的最大偏转角（度），防止飘带翻成“翅膀”
for act_name in ("Idle", "Drift", "Cast", "Channel"):
    rig.animation_data.action = bpy.data.actions[act_name]
    first, last = map(int, bpy.data.actions[act_name].frame_range)
    worst = (0.0, "", 0)
    for f in range(first, last + 1, 2):
        scene.frame_set(f)
        for pb in rig.pose.bones:
            if not pb.name.endswith(".3"):
                continue
            rest_dir = (SEG[pb.name][1] - SEG[pb.name][0]).normalized()
            now = (pb.tail - pb.head).normalized()
            angle = math.degrees(rest_dir.angle(now))
            if angle > worst[0]:
                worst = (angle, pb.name, f)
    print(f"MOTION CHECK {act_name}: max tail swing {worst[0]:.1f} deg at {worst[1]} frame {worst[2]}")
rig.animation_data.action = bpy.data.actions["Idle"]
scene.frame_set(1)

counts = {o.name: len(o.data.polygons) for o in rig.children if o.type == "MESH"}
print("NYX MESHES", counts, "BONES", len(arm_data.bones))
save_blend()

bpy.ops.object.select_all(action="DESELECT")
for obj in [root, *root.children_recursive]:
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True, export_yup=True,
                          export_apply=True, export_animation_mode="ACTIONS",
                          export_image_format="WEBP", export_image_quality=88)
print("EXPORTED", OUT, OUT.stat().st_size)

# ===== 游戏内 LOD：战斗俯视下角色约 110 像素高，减面、贴图减半、去掉针刃（飞剑由游戏原生绘制） =====
for obj in rig.children:
    ratio = next((r for key, r in GAME_LOD.items() if key in obj.name), None)
    if obj.type == "MESH" and ratio:
        mod = obj.modifiers.new("Game LOD", "DECIMATE")
        mod.ratio = ratio
        obj.modifiers.move(len(obj.modifiers) - 1, 0)
for image in bpy.data.images:
    if image.source == "FILE" and image.size[0] >= 512:
        image.scale(image.size[0] // 2, image.size[1] // 2)
needle.select_set(False)
bpy.ops.export_scene.gltf(filepath=str(GAME_OUT), export_format="GLB", use_selection=True, export_yup=True,
                          export_apply=True, export_animation_mode="ACTIONS",
                          export_image_format="WEBP", export_image_quality=85)
depsgraph = bpy.context.evaluated_depsgraph_get()
game_tris = sum(sum(len(p.vertices) - 2 for p in o.evaluated_get(depsgraph).data.polygons)
                for o in rig.children_recursive if o.type == "MESH")
print("EXPORTED", GAME_OUT, GAME_OUT.stat().st_size, "TRIS", game_tris)
