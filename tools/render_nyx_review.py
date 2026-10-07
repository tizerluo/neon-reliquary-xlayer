"""渲染 NYX 审图：正面、四分之三侧、侧面、背面与头部特写（Cycles + Metal）。

    blender -b art/nyx-void-artificer.blend --python tools/render_nyx_review.py
可选环境变量：NYX_SAMPLES（默认 64）、NYX_VIEWS（逗号分隔，如 front,detail）、NYX_SIZE（默认 900）。
"""

import math
import os
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "art" / "review" / "nyx"
OUT.mkdir(parents=True, exist_ok=True)
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
scene.cycles.samples = int(os.environ.get("NYX_SAMPLES", 64))
scene.cycles.use_denoising = True
size = int(os.environ.get("NYX_SIZE", 900))
scene.render.resolution_x = size
scene.render.resolution_y = int(size * 4 / 3)
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
for look in ("AgX - Medium High Contrast", "AgX - Punchy"):
    try:
        scene.view_settings.look = look
        break
    except TypeError:
        continue

world = bpy.data.worlds.new("Nyx studio")
scene.world = world
try:
    world.use_nodes = True
except AttributeError:
    pass
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.010, 0.010, 0.018, 1)
bg.inputs["Strength"].default_value = 1.0

floor_mat = bpy.data.materials.new("Review wet floor")
p = floor_mat.node_tree.nodes["Principled BSDF"]
p.inputs["Base Color"].default_value = (0.012, 0.013, 0.018, 1)
p.inputs["Roughness"].default_value = 0.22
p.inputs["Metallic"].default_value = 0.3
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
bpy.context.object.data.materials.append(floor_mat)


def area(name, location, power, color, size, target=(0, 0, 1.3)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.shape, data.size = power, color, "DISK", size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()


area("Key lavender", (-2.6, 3.4, 3.8), 440, (0.92, 0.88, 1.0), 2.6)
area("Fill cool", (2.8, 2.6, 1.6), 140, (0.62, 0.72, 1.0), 3.0)
area("Rim violet", (1.8, -3.0, 2.8), 620, (0.72, 0.45, 1.0), 1.6)
area("Rim cyan", (-2.2, -2.6, 2.2), 380, (0.35, 0.85, 1.0), 1.4)
area("Top", (0, 0.4, 4.6), 180, (0.9, 0.9, 1.0), 2.0)

# 19 枚针刃：双螺旋环绕（与网页端布局一致）
needle = bpy.data.objects.get("NYX_NEEDLE")
if needle:
    for i in range(19):
        strand = i % 2
        theta = i / 19 * math.tau * 2 + strand * math.pi
        radius = 0.62 + 0.08 * math.sin(i * 1.7)
        z = 0.95 + (i / 18) * 1.05
        clone = needle.copy()
        scene.collection.objects.link(clone)
        clone.parent = None
        clone.location = (math.cos(theta) * radius, math.sin(theta) * radius, z)
        tangent = Vector((-math.sin(theta), math.cos(theta), 0.18 * (1 if strand else -1)))
        clone.rotation_mode = "QUATERNION"
        clone.rotation_quaternion = tangent.to_track_quat("Y", "Z")
    needle.hide_render = True

cam_data = bpy.data.cameras.new("Review camera")
camera = bpy.data.objects.new("Review camera", cam_data)
scene.collection.objects.link(camera)
scene.camera = camera
VIEWS = {
    "front": ((0, 4.8, 1.30), (0, 0, 1.22), 50),
    "three-quarter": ((2.9, 3.9, 1.55), (0, 0, 1.22), 50),
    "side": ((4.8, 0.2, 1.30), (0, 0, 1.22), 50),
    "rear": ((0.4, -4.8, 1.40), (0, 0, 1.22), 50),
    "detail": ((0.42, 1.25, 2.02), (0, 0.02, 1.93), 85),
    "hands": ((1.25, 1.7, 1.45), (0.36, 0.12, 1.40), 70),
}
wanted = [v for v in os.environ.get("NYX_VIEWS", ",".join(VIEWS)).split(",") if v in VIEWS]
for name in wanted:
    loc, target, lens = VIEWS[name]
    camera.location = loc
    camera.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens
    scene.render.filepath = str(OUT / f"nyx-{name}.png")
    bpy.ops.render.render(write_still=True)
    print("REVIEW", scene.render.filepath)
