"""Render reproducible close-range front, side, and rear review plates.

Run with: blender -b art/oath-knight-highpoly-retopo.blend \
    --python tools/render_character_review.py
"""

from pathlib import Path
import math
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "art" / "review"
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.render.resolution_x = 720
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"


def is_knight_part(obj):
    current = obj
    while current:
        if current.name == "HERO":
            return True
        current = current.parent
    return False


for obj in bpy.data.objects:
    if obj.type == "MESH":
        obj.hide_render = not is_knight_part(obj)
    if obj.type == "LIGHT":
        bpy.data.objects.remove(obj, do_unlink=True)

world = bpy.data.worlds.new("Studio charcoal")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.08, 0.11, 0.15, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45


def area(name, location, power, color, size):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = power
    light_data.color = color
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    scene.collection.objects.link(light)
    light.location = location
    direction = Vector((0, 0, 2.05)) - light.location
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


area("Warm key", (-3.5, -4.5, 7), 1100, (1, 0.79, 0.60), 5)
area("Cyan fill", (3.0, -2.8, 4.6), 750, (0.30, 0.75, 1), 4)
area("Rear rim", (0.3, 3.2, 6), 1450, (0.85, 0.91, 1), 3)

camera_data = bpy.data.cameras.new("Review orthographic camera")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 4.7
camera = bpy.data.objects.new("Review orthographic camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera

for name, position in (
    ("front", (0, 8.5, 2.4)),
    ("side", (8.5, -1.5, 2.4)),
    ("rear", (0, -8.5, 2.4)),
):
    camera.location = position
    camera.rotation_euler = (Vector((0, 0, 2.05)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"oath-knight-{name}.png")
    bpy.ops.render.render(write_still=True)
    print("REVIEW RENDER", scene.render.filepath)

scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
camera_data.ortho_scale = 1.45
for name, position in (
    ("helmet-front", (0, 8.5, 3.4)),
    ("helmet-side", (8.5, 3.0, 3.4)),
):
    camera.location = position
    camera.rotation_euler = (Vector((0, 0, 3.30)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"oath-knight-{name}.png")
    bpy.ops.render.render(write_still=True)
    print("REVIEW RENDER", scene.render.filepath)

for name, position, focus, scale in (
    ("legs-front", (0, 8.5, 0.95), (0, 0, 1.05), 2.1),
    ("cape-rear", (0, -8.5, 1.55), (0, 0, 1.65), 2.8),
    ("equipment-front", (0, 8.5, 1.65), (0, 0, 1.65), 3.25),
):
    camera_data.ortho_scale = scale
    camera.location = position
    camera.rotation_euler = (Vector(focus) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"oath-knight-{name}.png")
    bpy.ops.render.render(write_still=True)
    print("REVIEW RENDER", scene.render.filepath)
