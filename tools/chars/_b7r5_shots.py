"""Boss 7（灰烬炽天使）第五轮：游戏条件模拟审图（Blender 一侧）+ 圣心特写补充视角。

游戏里（visual-game/glow.js + roster-bridge.js）Boss 7 只占屏幕一小块，材质经 tuneMaterial 再乘 1.1–1.2，
ACES（曝光 1.2）色调映射后叠“选择性辉光”：glowWeight 按材质名 / 是否带 emissiveMap 给权重，
半分辨率只画自发光件、UnrealBloom（strength 0.85, radius 0.4）模糊后以 1-exp(-x) → pow(0.8) 加色叠回。
本脚本把这套流程搬进 Blender：

  blender -b --python tools/chars/_b7r5_shots.py -- sim <GLB 文件名或绝对路径> <标签> [动作:帧] [自发光整体系数 damp]

1. 导入游戏版 GLB（读真实导出结果：合并后的网格、导出的自发光强度），按 tuneMaterial 的系数放大自发光，可选再乘 damp
   （0.5 复现游戏端目前的 EMISSIVE_DAMP 临时压暗）；
2. 俯视 game 视角（方位 0°、仰角 55°）的正交相机（游戏镜头就是正交），Boss 横向占画面 27%（≈ 1280×720 里 Boss 约 350 px 宽）；
3. 先渲主图（AgX + 曝光 +0.26 ≈ 游戏的 1.2，照明沿用审图灯光，地面改成暗色哑光），
   再关掉灯光 / 世界光，只留自发光并乘 glowWeight 渲“辉光图”（线性浮点），存 .npy；
4. 合成（辉光 + UnrealBloom + 加色叠回）在系统 Python 里做：tools/chars/_b7r5_simcomp.py。

另有 core 模式：圣心多角度特写（core 由 _b7r4_shots 的 detail 取景扩展）。
"""

import math
import os
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from kit import review  # noqa: E402
from kit.core import ROOT  # noqa: E402
from chars import _b7r4_shots as S  # noqa: E402


# ----- glow.js 的材质规则（逐字照搬） -----
def glow_weight(name, has_map):
    n = name.lower()
    if has_map:
        return 0.12
    if re.search(r"core|glow|eye|heart|slit", n):
        return 0.5
    if "hem" in n:
        return 0.3
    if re.search(r"inlay|circuit|rune|vein|seam", n):
        return 0.25
    return 0.06


def tune_gain(name):
    n = name.lower()
    if re.search(r"core|glow", n):
        return 1.2
    if "hem" in n:
        return 1.1
    if "inlay" in n:
        return 1.4
    return 1.1


def principled(m):
    if not m.node_tree:
        return None
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def emissive_info(m):
    """(是否自发光, 是否带发光贴图, Principled 节点)。"""
    p = principled(m)
    if p is None:
        return False, False, None
    es = p.inputs["Emission Strength"]
    ec = p.inputs["Emission Color"]
    has_map = ec.is_linked
    col = ec.default_value
    lit = es.default_value > 0 and (has_map or max(col[0], col[1], col[2]) > 0)
    return lit, has_map, p


def import_game(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    root = bpy.data.objects.new("BOSS_7", None)
    bpy.context.scene.collection.objects.link(root)
    for o in list(bpy.data.objects):
        if o.parent is None and o is not root and o.type in ("EMPTY", "MESH", "ARMATURE"):
            o.parent = root
    return root


def set_pose(spec):
    name, frame = spec.split(":")
    for arm in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
        ad = arm.animation_data or arm.animation_data_create()
        ad.action = bpy.data.actions[name]
        slots = getattr(ad, "action_suitable_slots", None)
        if slots and getattr(ad, "action_slot", None) is None:
            ad.action_slot = slots[0]
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()


def srgb_hex(h):
    """0xRRGGBB（sRGB）→ 线性 RGB（three.js 的 Color(hex) 同样按 sRGB 解码）。"""
    c = [((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def to_blender(v):
    """three.js（Y 向上，Boss 面朝 +Z 即面朝镜头）→ Blender（Z 向上，Boss 面朝 +Y）：(x, y, z) → (-x, z, y)。"""
    return Vector((-v[0], v[2], v[1]))


def game_lights(center):
    """把 roster-bridge.js 的灯光搬进来：4 盏方向光（强度直接对应 Blender 日光强度）、半球光（折成世界环境色）、
    battleEnvironment 的影棚灯板（不可见的自发光平面，只提供反射 / 环境光；environmentIntensity 0.9）。"""
    for o in list(bpy.data.objects):
        if o.type == "LIGHT":
            bpy.data.objects.remove(o)
    scene = bpy.context.scene
    for k, (hexcol, inten, pos) in enumerate(((0xefe8ff, 2.2, (-2.0, 4.8, 3.4)), (0xa070ff, 1.5, (-2.3, 3.3, -3.3)),
                                               (0x40e0ff, 0.8, (2.5, 2.7, -2.9)), (0x8f86c8, 0.5, (3, 1.5, 4)))):
        data = bpy.data.lights.new(f"Game sun {k}", "SUN")
        data.energy, data.color, data.angle = inten, srgb_hex(hexcol), math.radians(4)
        ob = bpy.data.objects.new(f"Game sun {k}", data)
        scene.collection.objects.link(ob)
        d = to_blender(pos).normalized()
        ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    # 半球光：天空色 0x9d8cff × 0.6，朝上的面受光最强——折成均匀世界光（约一半的立体角）
    sky = srgb_hex(0x9D8CFF)
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (sky[0] * 0.6 / math.pi * 0.5, sky[1] * 0.6 / math.pi * 0.5, sky[2] * 0.6 / math.pi * 0.5, 1)
    bg.inputs["Strength"].default_value = 1.0
    # 影棚灯板（battleEnvironment(bright=1.3)）：方向相同、距离放大 10 倍（环境贴图只看方向）
    bright = 1.3
    panels = [(6 * bright, 3 * bright, 0xECE6FF, 1.5 * bright, (0, 6, 3)), (1.2, 7, 0x8B5CF6, 3.2, (-4.5, 2, -3)),
              (1.2, 7, 0x2EE6FF, 2.0, (4.5, 2, -3)), (8, 1.4, 0x3B2A66, 1.1, (0, 0.4, 6)), (10, 4, 0xDFE6FF, 0.5 * bright, (0, 2.4, 7))]
    for k, (w, h, hexcol, gain, pos) in enumerate(panels):
        mat = bpy.data.materials.new(f"Env panel {k}")
        mat.use_nodes = True
        nt = mat.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*srgb_hex(hexcol), 1)
        em.inputs["Strength"].default_value = gain * 0.9
        outn = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
        me = bpy.data.meshes.new(f"Env panel {k}")
        me.from_pydata([(-w * 5, -h * 5, 0), (w * 5, -h * 5, 0), (w * 5, h * 5, 0), (-w * 5, h * 5, 0)], [], [(0, 1, 2, 3)])
        me.materials.append(mat)
        ob = bpy.data.objects.new(f"Env panel {k}", me)
        scene.collection.objects.link(ob)
        ob.location = center + to_blender(pos) * 10.0
        ob.rotation_euler = (center - ob.location).to_track_quat("Z", "Y").to_euler()
        ob.visible_camera = False
        ob.visible_shadow = False


def sim(glb, tag, pose="Idle:1", damp=1.0):
    path = Path(glb)
    if not path.is_absolute():
        path = ROOT / "visual-lab" / "assets" / "chars" / glb
    out = Path(os.environ["B7_OUT"]) if os.environ.get("B7_OUT") else ROOT / "art" / "review" / "chars" / "boss-7"
    out.mkdir(parents=True, exist_ok=True)
    W, H = int(os.environ.get("SIM_W", 1280)), int(os.environ.get("SIM_H", 720))
    frac = float(os.environ.get("SIM_FRAC", 0.27))
    samples = int(os.environ.get("SIM_SAMPLES", 48))
    root = import_game(path)
    set_pose(pose)
    scene = bpy.context.scene
    pts = S.world_points(root, 2)
    lo, hi = S.prepare(root, samples, W)
    scene.render.resolution_x, scene.render.resolution_y = W, H
    # 地面：游戏里是暗色地砖，审图用的湿地面会把灯光映成大亮斑——模拟图里直接去掉，背景用审图世界的暗色
    for o in bpy.data.objects:
        if o.name == "Review floor":
            o.hide_render = True
    game_lights(Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)))
    # 正交俯视相机：方位 0°、仰角 55°，Boss 投影宽度 = 画面宽度 × frac
    az, el = 0.0, float(os.environ.get("SIM_EL", 55))
    a, e = math.radians(az), math.radians(el)
    direction = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    fwd = -direction
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd).normalized()
    pr = pts @ np.array(right)
    pu = pts @ np.array(up)
    width = float(pr.max() - pr.min())
    ctr = Vector(((pts.min(axis=0) + pts.max(axis=0)) / 2).tolist())
    ctr += right * (float((pr.max() + pr.min()) / 2) - ctr.dot(right)) + up * (float((pu.max() + pu.min()) / 2) - ctr.dot(up))
    camera = bpy.data.objects["Review camera"]
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = width / frac
    camera.data.clip_start, camera.data.clip_end = 1.0, 400.0
    camera.location = ctr + direction * 60.0
    camera.rotation_euler = (ctr - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True          # 游戏里 Boss 画在透明画布上，背景是页面的暗色地砖；合成时再垫底色
    scene.view_settings.view_transform = os.environ.get("SIM_VT", "Filmic")      # 游戏是 ACES；Filmic 的高光滚降最接近
    try:
        scene.view_settings.look = os.environ.get("SIM_LOOK", "Medium High Contrast")
    except TypeError:
        scene.view_settings.look = "None"
    scene.view_settings.exposure = math.log2(1.2)          # 游戏曝光 1.2
    # --- 材质：按 tuneMaterial 放大自发光（可再乘 damp） ---
    base_strength = {}
    for m in bpy.data.materials:
        lit, has_map, p = emissive_info(m)
        if not lit:
            continue
        base_strength[m] = (p.inputs["Emission Strength"].default_value, has_map)
        p.inputs["Emission Strength"].default_value *= tune_gain(m.name) * damp
    # --- 主图 ---
    scene.render.filepath = str(out / f"{tag}_beauty.png")
    scene.cycles.use_denoising = True
    bpy.ops.render.render(write_still=True)
    print("SIM beauty", scene.render.filepath)
    # --- 辉光图：只留自发光 × glowWeight（线性、无色调映射） ---
    for m, (strength, has_map) in base_strength.items():
        p = principled(m)
        p.inputs["Emission Strength"].default_value = strength * tune_gain(m.name) * damp * glow_weight(m.name, has_map)
    for o in bpy.data.objects:
        if o.type == "LIGHT" or o.name.startswith("Env panel") or o.name == "Review floor":
            o.hide_render = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
    bg.inputs["Strength"].default_value = 0.0
    scene.view_settings.view_transform = "Standard"
    try:
        scene.view_settings.look = "None"
    except TypeError:
        pass
    scene.view_settings.exposure = 0.0
    scene.cycles.use_denoising = False
    scene.cycles.samples = 24
    exr = out / f"{tag}_glow.exr"
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(exr)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(exr))
    w, h = img.size
    buf = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(h, w, 4)[::-1, :, :3].astype(np.float16)
    np.save(out / f"{tag}_glow.npy", arr)
    exr.unlink()
    print("SIM glow", out / f"{tag}_glow.npy", arr.shape, "max", float(arr.max()))


# ----- 圣心特写（多角度） -----
def heart_shots(names):
    root = bpy.data.objects["BOSS_7"]
    arm = bpy.data.objects["BOSS_7_RIG"]
    arm.animation_data.action = bpy.data.actions["Idle"]
    bpy.context.scene.frame_set(1)
    from chars import boss_7 as R
    B = R.B0
    core = S.pose_point("Chest", B.on_torso(0, B.z(1.535), 0.15))
    extra = {
        "detail-heart": ((0.0, 1.0, 0.06), core, 50, 1.333, 2.6),
        "detail-heart-left": ((-0.55, 1.0, 0.10), core, 50, 1.333, 2.8),
        "detail-heart-right": ((0.55, 1.0, 0.10), core, 50, 1.333, 2.8),
        "detail-heart-low": ((0.20, 1.0, -0.35), core, 50, 1.333, 2.8),
        "detail-heart-wide": ((0.15, 1.0, 0.10), core, 50, 1.333, 5.2),
    }
    S.render(root, names, "", extra=extra)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    mode = args[0]
    if mode == "sim":
        glb, tag = args[1], args[2]
        pose = args[3] if len(args) > 3 else "Idle:1"
        damp = float(args[4]) if len(args) > 4 else 1.0
        sim(glb, tag, pose, damp)
    elif mode == "heart":
        heart_shots(args[1].split(","))


if __name__ == "__main__":
    main()
