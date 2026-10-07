"""掉落道具审图渲染（Blender Cycles + Metal）。

环境光模仿游戏的 battleEnvironment（深色背景 + 顶部柔光箱 + 灯条 + 低位紫色面板，等距柱状环境图，由 numpy 生成），
思路与飞剑审图一致。输出到 art/review/pickups/：
  <id>-front / -three-quarter / -top；圣物匣另有 chest-open（开盖 110°）、chest-halo（光环特写）；
  game-scale-hi.png：游戏机位俯视（正交，仰角与游戏相机一致，36 像素 / 米，3 倍超采样），
  由 tools/pickups/sheet.py 缩成 1:1 的 game-scale.png 并拼印样。
"""

import math
import os
import random
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art" / "review" / "pickups"

# 每个道具的取景：target = 视线目标（含悬浮高度）、dist = 相机距离、hover = 审图时抬高多少（碎片 / 圣瓶在游戏里悬浮）
FRAME = {
    "shard": dict(target=(0, 0, 0.50), dist=2.0, hover=0.50, ortho=1.0),
    "vial": dict(target=(0, 0, 0.55), dist=2.4, hover=0.55, ortho=1.2),
    "chest": dict(target=(0, 0, 0.50), dist=3.5, hover=0.0, ortho=1.7),
}
ACCENT = {"shard": "#86d9e6", "vial": "#87ffb5", "chest": "#ffd291"}

# 游戏机位：相机在目标的 (0, 34, 27) 方向（three.js：+Y 上、+Z 朝相机）；Blender 里即 (0, -27, 34)
GAME_DIR = Vector((0, -27, 34)).normalized()
GAME_PPM = 36.0                     # 像素 / 米（720p 画面：35.84 m 宽 ↔ 1280 px）
GAME_W, GAME_H, GAME_SS = 640, 360, 3
GAME_TIERS = ((0.7, 0.75), (1.0, 1.0), (1.6, 1.35))      # 碎片三档：(缩放, 发光倍数——网页端按档调亮度的模拟)


def _hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def _srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _env_image(accent_hex, cool=(0.18, 0.9, 1.0)):
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
    panel((0.85, 0.55, 0.40), math.radians(10), math.radians(38), cool, 4.0)               # 冷色灯条（身后右；游戏里是青色）
    panel((0.0, -0.95, 0.30), math.radians(40), math.radians(12), (0.23, 0.16, 0.40), 1.6)  # 低位紫色面板
    panel((0.0, -0.9, 0.55), math.radians(34), math.radians(18), (0.95, 0.92, 0.88), 1.6)  # 正面补光（看清正面细节）
    return img


def _setup(accent_hex, w, h, samples, cool=(0.18, 0.9, 1.0)):
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
    scene.view_settings.exposure = -0.5
    for look in ("AgX - Medium High Contrast", "AgX - Punchy"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue

    world = bpy.data.worlds.new("Pickup review env")
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    nt = world.node_tree
    nodes, links = nt.nodes, nt.links
    for n in list(nodes):
        nodes.remove(n)
    arr = _env_image(accent_hex, cool)
    ih, iw = arr.shape[:2]
    rgba = np.concatenate([arr, np.ones((ih, iw, 1))], axis=2).astype(np.float32)
    image = bpy.data.images.new("Pickup env", iw, ih, alpha=False, float_buffer=True)
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


def _camera(name, loc, target, lens=None, ortho=None, up_hint="Y"):
    scene = bpy.context.scene
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", up_hint).to_euler()
    scene.camera = cam
    return cam


def _shot(path, **cam_args):
    scene = bpy.context.scene
    cam = _camera("shot", **cam_args)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    print("REVIEW", path)


def _group_copy(objs, loc, yaw=0.0, scale=1.0, tilt=0.0, mats_override=None, tag="g"):
    """复制一整组节点（圣物匣是三个节点），挂在一个空物体下，便于整体摆放 / 自转 / 缩放。"""
    scene = bpy.context.scene
    root = bpy.data.objects.new(f"{tag}-root", None)
    scene.collection.objects.link(root)
    root.location = Vector(loc)
    root.rotation_euler = (tilt, 0, yaw)
    root.scale = (scale,) * 3
    out = []
    for o in objs.values():
        me = o.data
        if mats_override:
            me = me.copy()
            for i, m in enumerate(me.materials):
                me.materials[i] = mats_override.get(m.name, m)
        c = bpy.data.objects.new(f"{tag}-{o.name}", me)
        scene.collection.objects.link(c)
        c.parent = root
        c.location = o.location.copy()
        c.rotation_euler = o.rotation_euler.copy()
        out.append(c)
    return root, out


def render(pid, objs, samples=None):
    """单个道具的审图：front / three-quarter / top；圣物匣另出 open 与 halo 特写。"""
    samples = samples or int(os.environ.get("PICKUP_SAMPLES", 48))
    views = os.environ.get("PICKUP_VIEWS", "front,three-quarter,top,game1,open,halo").split(",")
    fr = FRAME[pid]
    OUT.mkdir(parents=True, exist_ok=True)
    # 圣物匣单件审图：青色灯条换成暖白，免得黄铜被映成绿色，便于判断造型本身（游戏机位总览仍用青色灯条）
    scene = _setup(ACCENT[pid], 1280, 800, samples, cool=(1.0, 0.86, 0.62) if pid == "chest" else (0.18, 0.9, 1.0))
    for o in objs.values():
        o.location.z += fr["hover"]
    tgt = Vector(fr["target"])
    d = fr["dist"]
    if "front" in views:
        _shot(OUT / f"{pid}-front.png", loc=tgt + Vector((0, -d, d * 0.10)), target=tgt, lens=55)
    if "three-quarter" in views:
        _shot(OUT / f"{pid}-three-quarter.png", loc=tgt + Vector((0.55, -0.72, 0.42)).normalized() * d, target=tgt, lens=55)
    if "top" in views:
        _shot(OUT / f"{pid}-top.png", loc=tgt + Vector((0, 0, 4)), target=tgt, ortho=fr["ortho"])
    if "game1" in views:    # 游戏相机仰角下的近景（单个道具，便于对照俯视读感）
        _shot(OUT / f"{pid}-gamecam.png", loc=tgt + GAME_DIR * d, target=tgt, lens=55)
    if pid == "chest":
        lid, halo = objs["CHEST_LID"], objs["CHEST_HALO"]
        if "open" in views:
            lid.rotation_euler = (math.radians(-110), 0, 0)
            _shot(OUT / "chest-open.png", loc=tgt + Vector((0.55, -0.72, 0.42)).normalized() * d * 1.05, target=tgt + Vector((0, 0.1, 0.1)), lens=55)
            _shot(OUT / "chest-open-side.png", loc=tgt + Vector((1.0, -0.12, 0.06)).normalized() * d * 1.05, target=tgt + Vector((0, 0.1, 0.1)), lens=55)
            lid.rotation_euler = (0, 0, 0)
        if "halo" in views:
            ht = halo.location + Vector((0, 0, 0.0))
            _shot(OUT / "chest-halo.png", loc=ht + Vector((0.25, -0.75, 0.55)).normalized() * 1.15, target=ht, lens=55)


def render_game(all_objs, samples=None, seed=11):
    """游戏机位：碎片三档（0.7 / 1.0 / 1.6）各 20 个 + 圣瓶 3 个 + 圣物匣 1 个，散布在深色地面上。"""
    samples = samples or int(os.environ.get("PICKUP_SAMPLES", 48))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "src").mkdir(exist_ok=True)
    # 游戏机位总览：主题灯条换成冷白、青灯条减弱，免得三种语义色（青 / 绿 / 金）被环境光互相染色
    scene = _setup("#c9d3ff", GAME_W * GAME_SS, GAME_H * GAME_SS, max(24, samples // 2), cool=(0.75, 0.85, 1.0))
    for objs in all_objs.values():
        for o in objs.values():
            o.hide_render = True
    rng = random.Random(seed)
    frame_w = GAME_W / GAME_PPM                  # 17.8 m
    frame_h = GAME_H / GAME_PPM / (GAME_DIR.z)   # 地面上的纵深范围：屏幕高度 / sin(仰角)
    placed = []

    def spot(radius):
        for _ in range(400):
            x = rng.uniform(-frame_w / 2 + 0.8, frame_w / 2 - 0.8)
            y = rng.uniform(-frame_h / 2 + 0.8, frame_h / 2 - 1.0)
            if all(math.hypot(x - px, y - py) > radius + pr for px, py, pr in placed):
                placed.append((x, y, radius))
                return x, y
        placed.append((0, 0, radius))
        return 0.0, 0.0

    # 先放大件，小件再避让
    x, y = spot(1.4)
    _group_copy(all_objs["chest"], (x, y, 0.0), yaw=rng.uniform(-0.5, 0.5), scale=1.0, tag="chest")
    for i in range(3):
        x, y = spot(0.9)
        _group_copy(all_objs["vial"], (x, y, 0.62 + 0.08 * math.sin(i * 2.1)), yaw=rng.uniform(0, math.tau), tag=f"vial{i}")
    shard_mats = {m.name: m for m in all_objs["shard"]["SHARD"].data.materials}
    for ti, (sc, gain) in enumerate(GAME_TIERS):
        over = {}
        for name, m in shard_mats.items():
            mm = m.copy()
            mm.name = f"{name} t{ti}"
            p = mm.node_tree.nodes["Principled BSDF"]
            p.inputs["Emission Strength"].default_value *= gain
            over[name] = mm
        for i in range(20):
            x, y = spot(0.42 * sc)
            _group_copy(all_objs["shard"], (x, y, 0.62 * sc + 0.1 + rng.uniform(-0.04, 0.06)), yaw=rng.uniform(0, math.tau),
                        scale=sc, mats_override=over, tag=f"shard{ti}-{i}")
    tgt = Vector((0, 0, 0))
    ortho = GAME_W / GAME_PPM
    cam_loc = tgt + GAME_DIR * 40
    _shot(OUT / "src" / "game-scale-hi.png", loc=cam_loc, target=tgt, ortho=ortho)
