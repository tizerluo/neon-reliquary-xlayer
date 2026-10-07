"""场地审图渲染（Blender Cycles + Metal，区域无关）。

灯光照搬 visual-game/arena-env.js 的布置：半球光（天 #9fb6c8 / 地 #080b12，0.55）+ 主光 #e6eeff（1.5，来自 (−24,40,20)）
+ 区域色轮廓光（0.7，来自 (18,24,−32)）+ 影棚环境（battleEnvironment：顶部柔光箱 + 主题色 / 青色灯条 + 低位紫色面板，×0.6），
three.js 的辐照度 ÷π 折算成 Blender 的瓦数。Blender 没有 ACES，用 AgX 近似；远处雾（40→115，#05080d）这里不模拟，
真实引擎里的观感以 three.js 里的实拍为准（见汇报）。

游戏机位：正交相机，眼睛在目标点上方 34、向南 27（俯角 ≈ 51.5°），视宽 36 单位，16:9。
占位人形 / 预警圈沿视线方向平移到所有几何前面——正交投影下屏幕位置不变，等价于“原生画布与角色画布永远画在场景之上”。
"""

import math
import os
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

from arenas import common as C
from arenas import textures as T

ROOT = C.ROOT
GAME_EYE = Vector((0, -27, 34))          # Blender 坐标（+Y 北）：眼睛相对目标的偏移（game：(0, 34, +27)）
GAME_W, GAME_H = 1280, 720
GAME_SCALE = 36.0                        # 视宽（单位）


# ===== 环境 / 灯光 =====
def _hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def _env_image(accent_hex):
    """等距柱状环境图（battleEnvironment 的复刻：Z 向上，+Y 为远离镜头的一侧）。"""
    W, H = 1024, 512
    u, v = (np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H
    PHI, THETA = np.meshgrid((u - 0.5) * math.tau, (v - 0.5) * math.pi)
    d = np.stack([-np.cos(THETA) * np.cos(PHI), np.cos(THETA) * np.sin(PHI), np.sin(THETA)], axis=-1)
    img = np.zeros((H, W, 3)) + 0.012
    accent = T.srgb_to_lin(_hex_rgb(accent_hex))
    cool = np.array([0.18, 0.9, 1.0])

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

    panel((0.0, -0.25, 1.0), math.radians(36), math.radians(20), (0.93, 0.90, 1.0), 3.0)
    panel((-0.85, 0.55, 0.40), math.radians(10), math.radians(38), accent, 6.0)
    panel((0.85, 0.55, 0.40), math.radians(10), math.radians(38), cool, 4.0)
    panel((0.0, -0.95, 0.30), math.radians(40), math.radians(12), (0.23, 0.16, 0.40), 1.6)
    return img


def setup(mood_hex, w, h, samples, exposure=0.0):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = "GPU"
    except Exception as error:      # 无 GPU 时回退 CPU
        print("GPU unavailable:", error)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = exposure
    for look in ("AgX - Base Contrast", "None"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue
    # 世界：影棚环境 ×0.6（漫反射 + 反射）+ 半球环境光；相机直接看到的背景是雾色
    world = bpy.data.worlds.new("Arena review")
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    nt = world.node_tree
    nodes, links = nt.nodes, nt.links
    for n in list(nodes):
        nodes.remove(n)
    arr = _env_image(mood_hex)
    ih, iw = arr.shape[:2]
    rgba = np.concatenate([arr, np.ones((ih, iw, 1))], axis=2).astype(np.float32)
    image = bpy.data.images.new("Arena env", iw, ih, alpha=False, float_buffer=True)
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    tex = nodes.new("ShaderNodeTexEnvironment")
    tex.image = image
    env = nodes.new("ShaderNodeBackground")
    env.inputs["Strength"].default_value = 0.6
    hemi = nodes.new("ShaderNodeBackground")
    sky = T.srgb_to_lin(_hex_rgb("#9fb6c8"))
    hemi.inputs["Color"].default_value = (*(sky * 0.55 / math.pi * 1.2), 1)
    add = nodes.new("ShaderNodeAddShader")
    dark = nodes.new("ShaderNodeBackground")
    dark.inputs["Color"].default_value = (*T.srgb_to_lin(_hex_rgb("#05080d")), 1)
    lp = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(tex.outputs["Color"], env.inputs["Color"])
    links.new(env.outputs["Background"], add.inputs[0])
    links.new(hemi.outputs["Background"], add.inputs[1])
    links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(add.outputs["Shader"], mix.inputs[1])
    links.new(dark.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])

    def sun(name, color_hex, strength, game_pos):
        d = bpy.data.lights.new(name, "SUN")
        d.color = tuple(T.srgb_to_lin(_hex_rgb(color_hex)))
        d.energy = strength
        d.angle = math.radians(2.0)
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        src = Vector((game_pos[0], -game_pos[2], game_pos[1]))
        o.rotation_euler = (-src).to_track_quat("-Z", "Y").to_euler()
        o.location = src
        return o

    sun("Key", "#e6eeff", 1.5 / math.pi, (-24, 40, 20))
    sun("Rim", mood_hex, 0.7 / math.pi, (18, 24, -32))
    return scene


# ===== 相机 =====
def camera(name, loc, target, ortho=None, lens=None, up="Y"):
    scene = bpy.context.scene
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    data.clip_start, data.clip_end = 0.5, 900
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens or 35
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", up).to_euler()
    scene.camera = cam
    return cam


def render(path, cam, size=None):
    scene = bpy.context.scene
    if size:
        scene.render.resolution_x, scene.render.resolution_y = size
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("REVIEW", path)


# ===== 占位物 =====
def _placeholder_specs():
    return {
        "Placeholder Grey": C.MatSpec("Placeholder Grey", base="#8a8f96", rough=0.6),
        "Placeholder Warn Fill": C.MatSpec("Placeholder Warn Fill", base="#000000", emit="#ff2a2a", strength=0.9, alpha=0.30, vcolor_alpha=False),
        "Placeholder Warn Edge": C.MatSpec("Placeholder Warn Edge", base="#000000", emit="#ff3030", strength=2.0, alpha=0.9),
    }


def make_actor_objects(actors, ring, shift):
    """actors：[(x, z)] 游戏坐标；ring：(x, z, 半径) 或 None。shift：Blender 向量（朝相机平移）。返回对象列表。"""
    specs = _placeholder_specs()
    mats = {n: C.make_material(s) for n, s in specs.items()}
    out = []
    cap = C.Mesh(1)
    r, H = 0.42, 2.3
    prof = [(r * math.sin(t), r * (1 - math.cos(t))) for t in np.linspace(0, math.pi / 2, 6)]
    prof += [(r * math.cos(t), H - r + r * math.sin(t)) for t in np.linspace(0, math.pi / 2, 6)][0:]
    for (x, z) in actors:
        with cap.at((x, 0, z)):
            cap.lathe("Placeholder Grey", prof, 14, smooth=True, share=True, cap_bottom=False, cap_top=False)
    if cap.F:
        o = C.to_blender(cap, "Placeholder actors", mats, specs)
        o.location += shift
        out.append(o)
    if ring:
        rx, rz, rr = ring
        rm = C.Mesh(2)
        seg = 96
        a = np.arange(seg) * math.tau / seg
        disc = [(rx + rr * math.cos(t), 0.04, rz + rr * math.sin(t)) for t in a]
        rm.quad_up("Placeholder Warn Fill", disc)
        for k in range(seg):
            k2 = (k + 1) % seg
            q = [(rx + (rr - 0.28) * math.cos(a[k]), 0.05, rz + (rr - 0.28) * math.sin(a[k])),
                 (rx + rr * math.cos(a[k]), 0.05, rz + rr * math.sin(a[k])),
                 (rx + rr * math.cos(a[k2]), 0.05, rz + rr * math.sin(a[k2])),
                 (rx + (rr - 0.28) * math.cos(a[k2]), 0.05, rz + (rr - 0.28) * math.sin(a[k2]))]
            rm.quad_up("Placeholder Warn Edge", q)
        o = C.to_blender(rm, "Placeholder ring", mats, specs)
        o.location += shift
        out.append(o)
    return out


# ===== 取景 =====
def game_shot(path, tx, tz, actors=None, ring=None, size=(GAME_W, GAME_H), scale=GAME_SCALE):
    """游戏机位：目标点 (tx, tz)（游戏坐标），正交，俯角 ≈ 51.5°。"""
    tgt = Vector((tx, -tz, 0))
    k = 2.2
    cam = camera("game", tgt + GAME_EYE * k, tgt, ortho=scale)
    to_cam = (cam.location - tgt).normalized()
    extra = make_actor_objects(actors or [], ring, to_cam * 55.0) if (actors or ring) else []
    render(path, cam, size)
    for o in extra:
        bpy.data.objects.remove(o)
    bpy.data.objects.remove(cam)


def free_shot(path, loc_game, target_game, lens=35, ortho=None, size=(1600, 900)):
    loc = Vector((loc_game[0], -loc_game[2], loc_game[1]))
    tgt = Vector((target_game[0], -target_game[2], target_game[1]))
    cam = camera("free", loc, tgt, ortho=ortho, lens=lens)
    render(path, cam, size)
    bpy.data.objects.remove(cam)


def debug_backfaces(objs):
    """调试：把所有对象的材质换成“背面粉红、正面灰”，用来找翻面。"""
    m = bpy.data.materials.new("DEBUG backface")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    em1 = nt.nodes.new("ShaderNodeEmission")
    em1.inputs["Color"].default_value = (1.0, 0.0, 0.8, 1)
    em2 = nt.nodes.new("ShaderNodeEmission")
    em2.inputs["Color"].default_value = (0.12, 0.12, 0.12, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    nt.links.new(em2.outputs["Emission"], mix.inputs[1])
    nt.links.new(em1.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    for o in objs.values():
        for i in range(len(o.data.materials)):
            o.data.materials[i] = m


def render_all(region, objs, out_dir, samples=None, only=None):
    """全套审图：game-*.png（含占位人形 + 红色预警圈）、overview*.png、floor-*.png、bounds-north.png。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = samples or int(os.environ.get("ARENA_SAMPLES", 48))
    scene = setup(region.MOOD, GAME_W, GAME_H, samples, exposure=float(os.environ.get("ARENA_EXPOSURE", -0.65)))
    if os.environ.get("ARENA_DEBUG") == "backface":
        debug_backfaces(objs)
    wanted = set(only or [])

    def want(n):
        return not wanted or n in wanted

    people = [(0, 0), (2.4, 1.2), (-2.2, 2.0)]

    def around(tx, tz):
        return [(tx + dx, tz + dz) for dx, dz in people]

    shots = {
        "game-center": (0, 0), "game-north": (0, -40), "game-east": (44, 0), "game-south": (0, 40),
        "game-west": (-44, 0), "game-northwest": (-44, -40), "game-northeast": (44, -40), "game-southeast": (44, 40),
    }
    for name, (tx, tz) in shots.items():
        if not want(name):
            continue
        act = [(min(max(x, -44), 44), min(max(z, -40), 40)) for x, z in around(tx, tz)]
        game_shot(out_dir / f"{name}.png", tx, tz, actors=act, ring=(tx + 5.0, tz - 2.5, 4.2) if name != "game-south" else (tx - 5.0, tz - 4.0, 4.2))
    if want("game-plain"):       # 不带占位物的中心机位（看纯场景）
        game_shot(out_dir / "game-plain.png", 0, -30)
    if want("overview"):
        scene.cycles.samples = max(24, samples // 2)
        cam = camera("top", (0, 0, 300), (0, 0, 0), ortho=150)
        render(out_dir / "overview.png", cam, (1500, 1500))
        bpy.data.objects.remove(cam)
        tgt = Vector((0, 0, 0))
        cam = camera("obl", tgt + GAME_EYE * 4, tgt, ortho=170)
        render(out_dir / "overview-oblique.png", cam, (1920, 1080))
        bpy.data.objects.remove(cam)
        scene.cycles.samples = samples
    if want("floor-detail"):
        free_shot(out_dir / "floor-detail.png", (22.5, 2.6, -2.5), (22.5, 0, -8.0), lens=38, size=(1600, 900))
        cam = camera("tile", (30, -8, 60), (30, -8, 0), ortho=12.0)
        render(out_dir / "floor-topdown.png", cam, (1200, 1200))
        bpy.data.objects.remove(cam)
        if hasattr(region, "EMBLEM_CENTER"):
            cam = camera("emb", (0, 0, 80), (0, 0, 0), ortho=34)
            render(out_dir / "emblem-topdown.png", cam, (1200, 1200))
            bpy.data.objects.remove(cam)
    if want("bounds-north"):
        free_shot(out_dir / "bounds-north.png", (34, 16, -20), (-2, 6.5, -50), lens=32, size=(1800, 1000))
        free_shot(out_dir / "bounds-north-low.png", (-14, 3.2, -30), (6, 7, -49), lens=30, size=(1800, 1000))
    return scene
