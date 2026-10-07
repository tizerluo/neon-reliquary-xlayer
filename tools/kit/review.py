"""角色工具包 · 审图渲染：按角色包围盒自动取景，Cycles + Metal，轮廓光使用角色主题色。

灯光、地面、相机都不挂在角色根节点下，因此不会被导出进 GLB。
"""

import math
import os

import bpy
from mathutils import Vector

from kit.core import ROOT


def _setup(accent, samples, size, aspect=4 / 3):
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
    scene.render.resolution_x = size
    scene.render.resolution_y = int(size * aspect)
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "AgX - Punchy"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue
    if bpy.data.objects.get("Review camera"):
        return scene, bpy.data.objects["Review camera"]
    world = bpy.data.worlds.new("Review studio")
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.010, 0.010, 0.018, 1)
    floor = bpy.data.materials.new("Review wet floor")
    p = floor.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.012, 0.013, 0.018, 1)
    p.inputs["Roughness"].default_value = 0.22
    p.inputs["Metallic"].default_value = 0.3
    me = bpy.data.meshes.new("Review floor")
    me.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(floor)
    scene.collection.objects.link(bpy.data.objects.new("Review floor", me))
    cam_data = bpy.data.cameras.new("Review camera")
    camera = bpy.data.objects.new("Review camera", cam_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera


def _lights(center, height, accent):
    scene = bpy.context.scene
    k = height / 2.1
    ac = tuple(0.35 + 0.65 * c for c in accent)

    def area(name, loc, power, color, size):
        if bpy.data.objects.get(name):
            return
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.color, data.shape, data.size = power * k * k, color, "DISK", size * k
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = center + Vector(loc) * k
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    area("Review key", (-2.6, 3.4, 2.6), 460, (0.95, 0.92, 1.0), 2.6)
    area("Review fill", (2.8, 2.6, 0.4), 150, (0.65, 0.74, 1.0), 3.0)
    area("Review rim accent", (1.8, -3.0, 1.6), 640, ac, 1.6)
    area("Review rim cool", (-2.2, -2.6, 1.0), 360, (0.45, 0.80, 1.0), 1.4)
    area("Review top", (0, 0.4, 3.4), 190, (0.9, 0.9, 1.0), 2.0)


def bounds(root):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    dg = bpy.context.evaluated_depsgraph_get()
    for o in [root, *root.children_recursive]:
        if o.type != "MESH" or o.hide_render:
            continue
        ev = o.evaluated_get(dg)
        for c in ev.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def render(cid, root, accent=(0.6, 0.6, 1.0), views=None, samples=None, size=None, tag=""):
    """渲染审图到 art/review/chars/<id>/；views 取 front/three-quarter/side/rear/detail/top/game。"""
    samples = samples or int(os.environ.get("CHAR_SAMPLES", 32))
    size = size or int(os.environ.get("CHAR_SIZE", 720))
    views = views or os.environ.get("CHAR_VIEWS", "front,three-quarter,rear,detail").split(",")
    out = ROOT / "art" / "review" / "chars" / cid
    out.mkdir(parents=True, exist_ok=True)
    scene, camera = _setup(accent, samples, size)
    lo, hi = bounds(root)
    center = (lo + hi) / 2
    height = max(hi.z - lo.z, hi.x - lo.x, hi.y - lo.y)
    _lights(Vector((center.x, center.y, lo.z + (hi.z - lo.z) * 0.6)), height, accent)
    d = height * 2.35
    top = Vector((0, 0, hi.z - (hi.z - lo.z) * 0.14))
    table = {
        "front": ((0, d, center.z * 0.95), center, 50),
        "three-quarter": ((d * 0.60, d * 0.80, center.z * 1.08), center, 50),
        "side": ((d, 0.05 * d, center.z), center, 50),
        "rear": ((0.08 * d, -d, center.z * 1.05), center, 50),
        "detail": ((0.22 * height, 0.62 * height, top.z + 0.04 * height), Vector((center.x, center.y, top.z)), 85),
        "top": ((0, d * 0.62, d * 0.9), center, 50),
        "game": ((0, d * 1.45, d * 1.85), Vector((center.x, center.y, lo.z + (hi.z - lo.z) * 0.4)), 28),
    }
    written = []
    for name in views:
        if name not in table:
            continue
        loc, target, lens = table[name]
        camera.location = Vector(loc) + Vector((center.x, center.y, 0))
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = lens
        path = out / f"{cid}{tag}-{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(path)
        print("REVIEW", path)
    return written
