"""Author a high-resolution knight source and bake it onto the playable rig.

The base script supplies the manually designed armor shapes and skeleton. This
pass keeps the low-resolution meshes as explicit retopology cages, sculpts
separate dense source meshes, unwraps each cage, and bakes tangent normals,
base color. The .blend retains both source and cages.

Run from the repository root with:
    blender --background --python tools/sculpt_retopo_bake.py
"""

from pathlib import Path
import math
import runpy

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "tools" / "build_visual_lab.py"))

OUT = ROOT / "visual-lab" / "assets" / "cathedral-slice.glb"
BAKES = ROOT / "visual-lab" / "assets" / "bakes"
BLEND = ROOT / "art" / "oath-knight-highpoly-retopo.blend"
BAKES.mkdir(parents=True, exist_ok=True)
BLEND.parent.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 8
scene.render.bake.use_selected_to_active = True
scene.render.bake.use_cage = True
scene.render.bake.cage_extrusion = 0.06
scene.render.bake.max_ray_distance = 0.12
scene.render.bake.margin = 8
scene.render.bake.normal_space = "TANGENT"
rig = bpy.data.objects["KNIGHT_RIG"]
rig.data.pose_position = "REST"
scene.frame_set(1)

source_collection = bpy.data.collections.new("HIGH POLY SCULPT SOURCES")
scene.collection.children.link(source_collection)
retopo_collection = bpy.data.collections.new("LOW POLY RETOPO CAGES")
scene.collection.children.link(retopo_collection)


def stroke_distance(x, z, a, b):
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)))
    return math.hypot(x - ax - t * dx, z - az - t * dz)


# Every mark below is placed deliberately in model coordinates. The eye, chest,
# shield, shoulder and shin relief respond to the original turnaround sheet.
CARVED_MARKS = [
    # Left and right helmet cheek bars.
    ((-0.31, 3.48), (-0.28, 3.24), 0.010, 0.011),
    ((0.31, 3.48), (0.28, 3.24), 0.010, 0.011),
    # Interrupted forge marks across breastplates.
    ((-0.45, 2.72), (-0.31, 2.65), 0.008, 0.009),
    ((0.44, 2.69), (0.32, 2.62), 0.008, 0.008),
    ((-0.36, 2.58), (-0.23, 2.53), 0.007, 0.006),
    # Narrow impact scores on the kite shield.
    ((-1.56, 2.53), (-1.42, 2.40), 0.008, 0.011),
    ((-1.05, 2.09), (-0.98, 1.95), 0.007, 0.008),
    # Pauldron and lower armor wear.
    ((-0.94, 3.02), (-0.83, 2.90), 0.008, 0.009),
    ((0.96, 3.03), (0.85, 2.91), 0.008, 0.009),
    ((-0.36, 0.88), (-0.31, 0.71), 0.009, 0.007),
    ((0.34, 0.87), (0.31, 0.69), 0.009, 0.007),
]


def sculpt_delta(point, normal, kind):
    x, y, z = point
    # A few frequency bands read as cast-metal grain and tooling under raking
    # light. They are actual changes to the high mesh, then baked to the cage.
    grain = (math.sin(x * 53 + z * 41 + y * 29) * 0.0017
             + math.sin(x * 111 - z * 67 + y * 39) * 0.0009)
    if kind == "cloth":
        falloff = max(0, min(1, (2.9 - z) / 2.6))
        fold = (0.016 * math.sin(x * 13 + z * 2.2)
                + 0.007 * math.sin(x * 31 - z * 4.5)) * falloff
        return fold + grain * 0.36
    dent = (math.sin(x * 19.1 + z * 13.7) * math.sin(y * 23.2 - z * 7.4)
            * (0.0025 if kind == "graphite" else 0.0014))
    if kind in ("graphite", "helmet") and normal.y > 0.17:
        for a, b, width, depth in CARVED_MARKS:
            distance = stroke_distance(x, z, a, b)
            if distance < width * 3:
                dent -= depth * math.exp(-((distance / width) ** 2))
                dent += depth * 0.18 * math.exp(-(((distance - width * 1.7) / width) ** 2))
    return grain + dent


def make_high_source(low, kind, bevel, cuts):
    high = low.copy()
    high.data = low.data.copy()
    source_collection.objects.link(high)
    high.name = "SCULPT | " + kind
    matrix = low.matrix_world.copy()
    high.parent = None
    high.matrix_world = matrix
    for modifier in list(high.modifiers):
        high.modifiers.remove(modifier)
    if bevel:
        modifier = high.modifiers.new("Hand-finished edge radius", "BEVEL")
        modifier.width = bevel
        modifier.segments = 4
        modifier.limit_method = "ANGLE"
        modifier.angle_limit = math.radians(35)
        bpy.ops.object.select_all(action="DESELECT")
        high.select_set(True)
        bpy.context.view_layer.objects.active = high
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    bm = bmesh.new()
    bm.from_mesh(high.data)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=cuts,
                              use_grid_fill=True)
    bm.to_mesh(high.data)
    bm.free()
    high.data.update()
    normals = [vertex.normal.copy() for vertex in high.data.vertices]
    for vertex, normal in zip(high.data.vertices, normals):
        world = high.matrix_world @ vertex.co
        vertex.co += normal * sculpt_delta(world, normal, kind)
    high.data.update()
    for face in high.data.polygons:
        face.use_smooth = True
    # The source is authored independently from the playable material. Its
    # spatial grain becomes diffuse information when the source is baked.
    source_material = low.data.materials[0].copy()
    source_material.name = "Sculpt source | " + kind
    high.data.materials[0] = source_material
    nodes = source_material.node_tree.nodes
    links = source_material.node_tree.links
    shader = nodes.get("Principled BSDF")
    coords = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 95 if kind == "cloth" else 40
    noise.inputs["Detail"].default_value = 3
    noise.inputs["Roughness"].default_value = 0.68
    links.new(coords.outputs["Object"], noise.inputs["Vector"])
    tint = nodes.new("ShaderNodeValToRGB")
    palette = {
        "graphite": ((0.055, 0.072, 0.086, 1), (0.097, 0.113, 0.128, 1)),
        "helmet": ((0.019, 0.027, 0.034, 1), (0.038, 0.048, 0.057, 1)),
        "gunmetal": ((0.062, 0.089, 0.105, 1), (0.105, 0.129, 0.146, 1)),
        "cloth": ((0.031, 0.038, 0.045, 1), (0.058, 0.063, 0.072, 1)),
    }
    tint.color_ramp.elements[0].position = 0.22
    tint.color_ramp.elements[0].color = palette[kind][0]
    tint.color_ramp.elements[1].position = 0.78
    tint.color_ramp.elements[1].color = palette[kind][1]
    links.new(noise.outputs["Fac"], tint.inputs["Fac"])
    links.new(tint.outputs["Color"], shader.inputs["Base Color"])
    return high


def unwrap_retopology(low):
    # The visible asset keeps these authored, low-density contours; the source
    # remains separate in the .blend and is never shipped to the browser.
    for layer in list(low.data.uv_layers):
        low.data.uv_layers.remove(layer)
    low.data.uv_layers.new(name="Retopo bake atlas")
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.012)
    bpy.ops.object.mode_set(mode="OBJECT")
    low.data.uv_layers.active_index = 0


def image_target(material, name, width, noncolor):
    image = bpy.data.images.new(name, width=width, height=width,
                                alpha=False, float_buffer=False)
    image.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.name = name
    node.image = image
    material.node_tree.nodes.active = node
    return image, node


def bake_map(low, high, image, node, bake_type):
    material = low.data.materials[0]
    material.node_tree.nodes.active = node
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    scene.render.bake.use_selected_to_active = True
    if bake_type == "DIFFUSE":
        scene.render.bake.use_pass_direct = False
        scene.render.bake.use_pass_indirect = False
        scene.render.bake.use_pass_color = True
    bpy.ops.object.bake(type=bake_type)
    image.filepath_raw = str(BAKES / (image.name.replace(" ", "-").lower() + ".png"))
    image.file_format = "PNG"
    image.save()
    image.pack()
    print("BAKED", bake_type, image.filepath_raw)


def connect_bakes(material, color_node, normal_node):
    shader = material.node_tree.nodes.get("Principled BSDF")
    links = material.node_tree.links
    links.new(color_node.outputs["Color"], shader.inputs["Base Color"])
    if normal_node:
        normal_map = material.node_tree.nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = 0.36 if material.name.startswith("Baked Helmet") else 0.72
        links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])


specs = (
    ("Forged graphite armor", "graphite", 0.011, 8, 2048),
    ("Helmet matte alloy", "helmet", 0.006, 8, 1024),
    ("Oxidized gunmetal", "gunmetal", 0.008, 5, 1024),
    ("Charcoal woven mantle", "cloth", 0.0, 7, 1024),
)
high_sources = []
retopo_meshes = []
for material_name, kind, bevel, cuts, resolution in specs:
    low = bpy.data.objects["KNIGHT_RIG | " + material_name]
    original_material = low.data.materials[0]
    modifier = next(m for m in low.modifiers if m.type == "ARMATURE")
    modifier.show_render = False
    modifier.show_viewport = False
    high = make_high_source(low, kind, bevel, cuts)
    high_sources.append(high)
    new_material = original_material.copy()
    new_material.name = "Baked " + material_name
    low.data.materials[0] = new_material
    unwrap_retopology(low)
    retopo_meshes.append(low)
    color, color_node = image_target(new_material, kind + " sculpt albedo", resolution, False)
    bake_map(low, high, color, color_node, "DIFFUSE")
    normal_node = None
    if kind != "cloth":
        normal, normal_node = image_target(new_material, kind + " sculpt normal", resolution, True)
        bake_map(low, high, normal, normal_node, "NORMAL")
    connect_bakes(new_material, color_node, normal_node)
    print("SCULPT RETOPO", kind, "high faces", len(high.data.polygons),
          "low faces", len(low.data.polygons), "atlas", resolution)

# Store editable high sources, retopology cages, the rig, and all packed maps.
for low in retopo_meshes:
    if low.name in bpy.context.collection.objects:
        bpy.context.collection.objects.unlink(low)
    retopo_collection.objects.link(low)
    modifier = next(m for m in low.modifiers if m.type == "ARMATURE")
    modifier.show_render = True
    modifier.show_viewport = True
for high in high_sources:
    high.hide_set(True)
    high.hide_render = True
rig.data.pose_position = "POSE"
for image in bpy.data.images:
    if image.source == "FILE" and not image.packed_file:
        image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
print("SAVED SOURCE", BLEND)

# The browser receives only the animated, baked retopology. Keep the source in
# the .blend for further manual work and exact bake reproduction.
for high in high_sources:
    bpy.data.objects.remove(high, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.data.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", export_yup=True,
                          export_apply=True, export_animation_mode="ACTIONS")
print("EXPORTED BAKED RETOPO", OUT, OUT.stat().st_size)
