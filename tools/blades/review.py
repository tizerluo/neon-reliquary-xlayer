"""飞剑审图渲染（Blender Cycles + Metal）。

环境光模仿游戏里的 battleEnvironment：深色背景 + 顶部柔光箱 + 主题色 / 青色灯条 + 低位紫色面板，
用 numpy 生成等距柱状环境图，所有位置的飞剑受光一致（与游戏里无限远的环境贴图一致）。
输出到 art/review/blades/：<id>-top / -three-quarter / -detail，以及蜂群源图 src/<id>-swarm-hi.png
（3 倍超采样，由 tools/blades/sheet.py 缩成游戏分辨率的 <id>-swarm.png 并拼印样）。
"""

import math
import os
import random
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art" / "review" / "blades"

# 蜂群：画面 24 m × 16 m、480 × 320 像素 → 整把剑（1.4 m）约 28 像素；3 倍超采样
SWARM_W, SWARM_H, SWARM_SS, SWARM_FRAME_W = 480, 320, 3, 24.0
SWARM_COUNT, SWARM_SEED = 40, 7


def _hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def _srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _env_image(accent_hex):
    """等距柱状环境图：Z 向上，+Y 为画面上方（远离相机一侧）。"""
    W, H = 1024, 512
    u = (np.arange(W) + 0.5) / W
    v = (np.arange(H) + 0.5) / H
    phi = (u - 0.5) * math.tau
    theta = (v - 0.5) * math.pi
    PHI, THETA = np.meshgrid(phi, theta)
    d = np.stack([-np.cos(THETA) * np.cos(PHI), np.cos(THETA) * np.sin(PHI), np.sin(THETA)], axis=-1)

    img = np.zeros((H, W, 3)) + 0.012
    accent = _srgb_to_lin(_hex_rgb(accent_hex))

    def panel(center, half_u, half_v, color, gain):
        c = np.array(center, float)
        c /= np.linalg.norm(c)
        up = np.array([0, 0, 1.0]) if abs(c[2]) < 0.95 else np.array([0, 1.0, 0])
        a = np.cross(up, c)
        a /= np.linalg.norm(a)
        b = np.cross(c, a)
        x, y, z = d @ a, d @ b, d @ c
        ok = z > 0.05
        px = np.where(ok, x / np.maximum(z, 1e-3), 9)
        py = np.where(ok, y / np.maximum(z, 1e-3), 9)
        fall = np.clip((1 - np.abs(px) / math.tan(half_u)) * 4, 0, 1) * np.clip((1 - np.abs(py) / math.tan(half_v)) * 4, 0, 1)
        img[:] += fall[..., None] * np.array(color)[None, None, :] * gain

    panel((0.0, -0.25, 1.0), math.radians(36), math.radians(20), (0.93, 0.90, 1.0), 3.0)   # 顶部柔光箱
    panel((-0.85, 0.55, 0.40), math.radians(10), math.radians(38), accent, 6.0)              # 主题色灯条（身后左）
    panel((0.85, 0.55, 0.40), math.radians(10), math.radians(38), (0.18, 0.9, 1.0), 4.0)   # 青色灯条（身后右）
    panel((0.0, -0.95, 0.30), math.radians(40), math.radians(12), (0.23, 0.16, 0.40), 1.6)  # 低位紫色面板
    return img


def _setup(accent_hex, w, h, samples):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for device in prefs.devices:
            device.use = True
        scene.cycles.device = "GPU"
    except Exception as error:  # 无 GPU 时回退 CPU
        print("GPU unavailable:", error)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = -0.5          # 强发光不被 AgX 洗成白色，主题色看得出来
    for look in ("AgX - Medium High Contrast", "AgX - Punchy"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue

    # 世界：环境图（反射 / 照明）+ 相机射线看到的深色背景
    world = bpy.data.worlds.new("Blade review env")
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    nt = world.node_tree
    nodes, links = nt.nodes, nt.links
    for n in list(nodes):
        nodes.remove(n)
    arr = _env_image(accent_hex)
    ih, iw = arr.shape[:2]
    rgba = np.concatenate([arr, np.ones((ih, iw, 1))], axis=2).astype(np.float32)
    image = bpy.data.images.new("Blade env", iw, ih, alpha=False, float_buffer=True)
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    tex = nodes.new("ShaderNodeTexEnvironment")
    tex.image = image
    bg_env = nodes.new("ShaderNodeBackground")
    bg_env.inputs["Strength"].default_value = 1.0
    bg_dark = nodes.new("ShaderNodeBackground")
    bg_dark.inputs["Color"].default_value = (0.012, 0.014, 0.022, 1)
    lp = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(tex.outputs["Color"], bg_env.inputs["Color"])
    links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(bg_env.outputs["Background"], mix.inputs[1])
    links.new(bg_dark.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])

    # 地面：深蓝黑、微湿
    floor_mat = bpy.data.materials.new("Review floor")
    try:
        floor_mat.use_nodes = True
    except AttributeError:
        pass
    p = floor_mat.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.010, 0.013, 0.022, 1)
    p.inputs["Metallic"].default_value = 0.0
    p.inputs["Roughness"].default_value = 0.75
    p.inputs["Specular IOR Level"].default_value = 0.25
    me = bpy.data.meshes.new("Review floor")
    me.from_pydata([(-60, -60, -0.02), (60, -60, -0.02), (60, 60, -0.02), (-60, 60, -0.02)], [], [(0, 1, 2, 3)])
    me.materials.append(floor_mat)
    floor = bpy.data.objects.new("Review floor", me)
    scene.collection.objects.link(floor)
    return scene


def _camera(name, loc, target, lens=None, ortho=None):
    scene = bpy.context.scene
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
        cam.location = Vector(loc)
        cam.rotation_euler = (0, 0, 0)               # 正俯视：+X 向右，+Y 向上
    else:
        data.lens = lens
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def _shot(path, cam_args):
    scene = bpy.context.scene
    cam = _camera("shot", **cam_args)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    print("REVIEW", path)


def render(cid, obj, accent_hex, detail, views=None, samples=None):
    """views 取 top, three-quarter, detail, swarm；样本数可由 BLADE_SAMPLES 覆盖。"""
    samples = samples or int(os.environ.get("BLADE_SAMPLES", 48))
    views = views or os.environ.get("BLADE_VIEWS", "top,three-quarter,detail,swarm").split(",")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "src").mkdir(exist_ok=True)
    scene = _setup(accent_hex, 1280, 800, samples)
    mid = Vector((0.15, 0, 0))

    if "top" in views:
        _shot(OUT / f"{cid}-top.png", dict(loc=(mid.x, 0, 4), target=mid, ortho=1.75))
    if "three-quarter" in views:
        _shot(OUT / f"{cid}-three-quarter.png",
              dict(loc=mid + Vector((0.55, -1.55, 1.15)), target=mid + Vector((0.0, 0, -0.05)), lens=38))
    if "detail" in views:
        tgt, dist = detail
        _shot(OUT / f"{cid}-detail.png",
              dict(loc=Vector(tgt) + Vector((0.22, -0.62, 0.55)).normalized() * dist, target=tgt, lens=55))
    if "swarm" in views:
        scene.render.resolution_x, scene.render.resolution_y = SWARM_W * SWARM_SS, SWARM_H * SWARM_SS
        scene.cycles.samples = max(24, samples // 2)
        rng = random.Random(SWARM_SEED)
        obj.hide_render = True
        copies = []
        for i in range(SWARM_COUNT):
            c = bpy.data.objects.new(f"swarm{i}", obj.data)
            scene.collection.objects.link(c)
            c.location = (rng.uniform(-8.5, 8.5), rng.uniform(-5.2, 5.2), 0.10 + rng.uniform(0, 0.05))
            c.rotation_euler = (0, 0, rng.uniform(0, math.tau))
            copies.append(c)
        _shot(OUT / "src" / f"{cid}-swarm-hi.png", dict(loc=(0, 0, 8), target=(0, 0, 0), ortho=SWARM_FRAME_W))
        for c in copies:
            bpy.data.objects.remove(c)
        obj.hide_render = False
