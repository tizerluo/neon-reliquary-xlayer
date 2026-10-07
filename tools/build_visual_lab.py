"""Build a small, original PBR glTF art slice for the visual research page.

Run with: blender --background --python tools/build_visual_lab.py
The exported geometry is deliberately modest; the source script is the asset source.
"""

from pathlib import Path
import math
import random
import shutil
import tempfile

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "visual-lab" / "assets" / "cathedral-slice.glb"
TEXTURE_DIR = Path(tempfile.mkdtemp(prefix="reliquary-materials-"))
random.seed(28)
bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, color, metal=0, rough=0.5, glow=None, strength=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    if glow:
        p.inputs["Emission Color"].default_value = (*glow, 1)
        p.inputs["Emission Strength"].default_value = strength
    return m


stone = material("Wet basalt | uneven slabs", (0.055, 0.082, 0.105), 0.22, 0.3)
stone_dark = material("Drier chipped basalt", (0.075, 0.082, 0.094), 0.08, 0.72)
wall = material("Charcoal cathedral stone", (0.045, 0.058, 0.072), 0.12, 0.69)
steel = material("Brushed oath steel", (0.34, 0.45, 0.52), 0.88, 0.28)
steel_light = material("Polished plate edges", (0.65, 0.78, 0.8), 0.95, 0.22)
steel_dark = material("Oxidized gunmetal", (0.075, 0.11, 0.15), 0.77, 0.44)
gold = material("Aged brass inlay", (0.43, 0.28, 0.11), 0.88, 0.34)
graphite = material("Forged graphite armor", (0.075, 0.095, 0.12), 0.62, 0.43)
helmet_metal = material("Helmet matte alloy", (0.025, 0.036, 0.045), 0.32, 0.76)
cloth = material("Charcoal woven mantle", (0.044, 0.050, 0.057), 0.03, 0.88)
cyan = material("Oath circuit cyan", (0.05, 0.44, 0.54), 0.3, 0.26, (0.06, 0.85, 1.0), 1.1)
visor_glass = material("Visor smoked glass", (0.001, 0.003, 0.006), 0.05, 0.94)
visor_cyan = material("Visor focused cyan", (0.012, 0.24, 0.34), 0.10, 0.42,
                      (0.016, 0.36, 0.52), 0.52)
cyan_thread = material("Mantle woven cyan thread", (0.015, 0.14, 0.18),
                       0.08, 0.7, (0.02, 0.35, 0.42), 0.35)
magenta = material("Hostile circuit magenta", (0.28, 0.03, 0.13), 0.22, 0.37, (1.0, 0.08, 0.35), 1.1)
obsidian = material("Enemy obsidian armor", (0.085, 0.053, 0.074), 0.58, 0.35)


def surface_image(name, colors, noncolor=False):
    image = bpy.data.images.new(name, width=256, height=256, alpha=True)
    image.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    image.pixels.foreach_set([channel for rgb in colors for channel in (*rgb, 1.0)])
    image.update()
    image.filepath_raw = str(TEXTURE_DIR / f"{name.replace(' ', '-').lower()}.png")
    image.file_format = "PNG"
    image.save()
    return image


def textured_surface(mat, base, normal, roughness):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    principled = nodes.get("Principled BSDF")
    for image, input_name in ((base, "Base Color"), (roughness, "Roughness")):
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = image
        links.new(texture.outputs["Color"], principled.inputs[input_name])
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = normal
    normal_node = nodes.new("ShaderNodeNormalMap")
    normal_node.inputs["Strength"].default_value = 0.52
    links.new(texture.outputs["Color"], normal_node.inputs["Color"])
    links.new(normal_node.outputs["Normal"], principled.inputs["Normal"])


heights = []
for y in range(256):
    for x in range(256):
        u, v = x / 256, y / 256
        waves = (math.sin(u * math.tau * 6 + math.sin(v * math.tau * 3) * 1.6) * 0.18
                 + math.sin(v * math.tau * 9 + u * math.tau * 2) * 0.09)
        fissure = max(0, 0.035 - abs(math.sin((u * 3 + v * 2) * math.tau))) * 2.2
        grain = ((x * 157 + y * 89) % 37) / 37 * 0.045
        heights.append(0.48 + waves - fissure + grain)

wet_color, dry_color, rough_map, normal_map = [], [], [], []
for y in range(256):
    for x in range(256):
        i = y * 256 + x
        h = heights[i]
        tone = 0.8 + h * 0.42
        wet_color.append((0.065 * tone, 0.105 * tone, 0.13 * tone))
        dry_color.append((0.082 * tone, 0.087 * tone, 0.092 * tone))
        rough_map.append((0.24 + h * 0.16,) * 3)
        dx = heights[y * 256 + (x + 1) % 256] - heights[y * 256 + (x - 1) % 256]
        dy = heights[((y + 1) % 256) * 256 + x] - heights[((y - 1) % 256) * 256 + x]
        normal_map.append((0.5 - dx * 1.25, 0.5 - dy * 1.25, 1.0))

normal_image = surface_image("Chipped stone normal", normal_map, True)
rough_image = surface_image("Puddled stone roughness", rough_map, True)
textured_surface(stone, surface_image("Wet blue basalt", wet_color), normal_image, rough_image)
textured_surface(stone_dark, surface_image("Dry blue basalt", dry_color), normal_image,
                 surface_image("Dry basalt roughness", [(0.64,) * 3] * (256 * 256), True))

# Small, reusable PBR metal maps provide scratches and variable oxidation at
# almost no geometry cost. The plate silhouette and layered forms stay 3D.
metal_height = [0.0] * (256 * 256)
wear_rng = random.Random(307)
for _ in range(105):
    sx, sy = wear_rng.randrange(256), wear_rng.randrange(256)
    length = wear_rng.randrange(6, 38)
    lean = wear_rng.uniform(-0.28, 0.28)
    for step in range(length):
        px = (sx + step) % 256
        py = (sy + int(step * lean)) % 256
        metal_height[py * 256 + px] = wear_rng.uniform(-0.22, -0.10)

armor_normals, armor_roughness = [], []
for y in range(256):
    for x in range(256):
        idx = y * 256 + x
        grain = (math.sin(x * 0.34 + math.sin(y * 0.13)) * 0.016
                 + math.sin(y * 0.47 + x * 0.08) * 0.009)
        metal_height[idx] += grain
        h = metal_height[idx]
        armor_roughness.append((max(0.18, min(0.78, 0.40 + h * 0.45
                                 + (x * 29 + y * 43) % 17 / 200)),) * 3)
        dx = metal_height[y * 256 + (x + 1) % 256] - metal_height[y * 256 + (x - 1) % 256]
        dy = metal_height[((y + 1) % 256) * 256 + x] - metal_height[((y - 1) % 256) * 256 + x]
        armor_normals.append((0.5 - dx * 1.0, 0.5 - dy * 1.0, 1.0))

metal_normal = surface_image("Hand forged plate normal", armor_normals, True)
metal_rough = surface_image("Hand forged plate roughness", armor_roughness, True)
for mat, label, base in ((graphite, "Graphite plate", (0.075, 0.095, 0.12)),
                         (gold, "Aged brass", (0.43, 0.28, 0.11))):
    colors = []
    for y in range(256):
        for x in range(256):
            h = metal_height[y * 256 + x]
            variation = 0.87 + (math.sin(x * 0.11 + y * 0.075) + 1) * 0.055
            variation += h * 1.6
            colors.append(tuple(max(0, min(1, c * variation)) for c in base))
    textured_surface(mat, surface_image(label + " albedo", colors), metal_normal, metal_rough)

weave_color, weave_normal, weave_rough = [], [], []
for y in range(256):
    for x in range(256):
        thread = 0.5 + math.sin(x * 0.75) * math.sin(y * 0.74) * 0.11
        faded = 0.84 + math.sin((x + y) * 0.033) * 0.11
        weave_color.append((0.065 * faded, 0.071 * faded, 0.078 * faded))
        weave_normal.append((0.5 + (thread - 0.5) * 0.25,
                             0.5 - (thread - 0.5) * 0.25, 1.0))
        weave_rough.append((0.86 + (thread - 0.5) * 0.12,) * 3)
textured_surface(cloth, surface_image("Frayed mantle weave", weave_color),
                 surface_image("Frayed mantle normal", weave_normal, True),
                 surface_image("Frayed mantle roughness", weave_rough, True))


def group(name):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    return obj


arena = group("ARENA")
hero = group("HERO")
enemy = group("ENEMY")


def finish(obj, name, mat, parent, bevel=0):
    obj.name = name
    obj.data.materials.append(mat)
    obj.parent = parent
    if bevel:
        mod = obj.modifiers.new("Worn machined edge", "BEVEL")
        mod.width = bevel
        mod.segments = 2 if parent == arena else 1
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def box(name, xyz, size, mat, parent, bevel=0.03, rotate=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
    obj = bpy.context.object
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rotate:
        obj.rotation_euler = rotate
    return finish(obj, name, mat, parent, bevel)


def cyl(name, xyz, radius, depth, mat, parent, vertices=16, rotate=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=xyz)
    obj = bpy.context.object
    if rotate:
        obj.rotation_euler = rotate
    return finish(obj, name, mat, parent, 0.012)


def cone(name, xyz, r1, r2, depth, mat, parent, vertices=12, rotate=None):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=depth, location=xyz)
    obj = bpy.context.object
    if rotate:
        obj.rotation_euler = rotate
    return finish(obj, name, mat, parent)


def ring(name, xyz, radius, tube, mat, parent):
    bpy.ops.mesh.primitive_torus_add(major_segments=24, minor_segments=6,
                                    location=xyz, rotation=(math.pi / 2, 0, 0),
                                    major_radius=radius, minor_radius=tube)
    return finish(bpy.context.object, name, mat, parent)


def rod(name, start, end, radius, mat, parent, vertices=10):
    a, b = Vector(start), Vector(end)
    center = (a + b) * 0.5
    obj = cyl(name, center, radius, (b - a).length, mat, parent, vertices)
    obj.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    return obj


def cut_plate(name, outline, front_y, thickness, mat, parent, bevel=0.012,
              crown=0.0):
    """Extrude an X/Z silhouette; optional concentric rings sculpt a convex face."""
    count = len(outline)
    vertices = [(x, front_y, z) for x, z in outline]
    if crown:
        cx = sum(x for x, _ in outline) / count
        cz = sum(z for _, z in outline) / count
        for scale, rise in ((0.84, 0.70), (0.48, 1.0)):
            vertices.extend((cx + (x - cx) * scale,
                             front_y + crown * rise,
                             cz + (z - cz) * scale)
                            for x, z in outline)
    back_start = len(vertices)
    vertices += [(x, front_y - thickness, z) for x, z in outline]
    signed_area = sum(outline[i][0] * outline[(i + 1) % count][1]
                      - outline[(i + 1) % count][0] * outline[i][1]
                      for i in range(count))
    clockwise = signed_area < 0
    front_start = 2 * count if crown else 0
    front = tuple(range(front_start, front_start + count))
    back = tuple(range(back_start, back_start + count))
    faces = [front if clockwise else tuple(reversed(front)),
             tuple(reversed(back)) if clockwise else back]
    if crown:
        for start_a, start_b in ((0, count), (count, 2 * count)):
            for i in range(count):
                j = (i + 1) % count
                face = (start_a + i, start_a + j,
                        start_b + j, start_b + i)
                faces.append(face if clockwise else tuple(reversed(face)))
    for i in range(count):
        j = (i + 1) % count
        edge = (i, back_start + i, back_start + j, j)
        faces.append(edge if clockwise else tuple(reversed(edge)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Metal grain projection")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            point = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (point.x * 1.3, point.z * 1.3)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat, parent, 0 if crown else bevel)


def side_plate(name, outline, side, outer_x, thickness, mat, parent):
    """Hand-authored Y/Z cheek silhouette joining the visor and back shell."""
    count = len(outline)
    cy = sum(y for y, _ in outline) / count
    cz = sum(z for _, z in outline) / count
    rings = ((outer_x, 1.0), (outer_x + 0.028, 0.82),
             (outer_x + 0.044, 0.48), (outer_x - thickness, 1.0))
    verts = [(side * x, cy + (y - cy) * scale, cz + (z - cz) * scale)
             for x, scale in rings for y, z in outline]
    outer = tuple(reversed(range(2 * count, 3 * count))) if side > 0 else tuple(range(2 * count, 3 * count))
    back = tuple(i + 3 * count for i in reversed(range(count))) if side > 0 else tuple(range(3 * count, 4 * count))
    faces = [outer, back]
    for ring_a, ring_b in ((0, 1), (1, 2), (3, 0)):
        for i in range(count):
            j = (i + 1) % count
            edge = (ring_a * count + i, ring_a * count + j,
                    ring_b * count + j, ring_b * count + i)
            faces.append(tuple(reversed(edge)) if side > 0 else edge)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Helmet cheek projection")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            point = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (point.y * 1.3, point.z * 1.3)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat, parent, 0)


def fold(name, outline, mat, parent, thickness=0.035):
    """A swept fabric flap, including an underside visible in a rear orbit."""
    count = len(outline)
    vertices = outline + [(x, y - thickness, z) for x, y, z in outline]
    signed_area = sum(outline[i][0] * outline[(i + 1) % count][2]
                      - outline[(i + 1) % count][0] * outline[i][2]
                      for i in range(count))
    clockwise = signed_area < 0
    front = tuple(range(count)) if clockwise else tuple(reversed(range(count)))
    back = tuple(reversed(range(count, count * 2))) if clockwise else tuple(range(count, count * 2))
    faces = [front, back]
    for i in range(count):
        j = (i + 1) % count
        edge = (i, i + count, j + count, j)
        faces.append(edge if clockwise else tuple(reversed(edge)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat, parent)


def cape_panel(name, side, mat, parent):
    """Hand-shaped, two-sided fabric with broad folds and an uneven frayed hem."""
    columns, rows = 20, 14
    front = []
    for row in range(rows + 1):
        t = row / rows
        for col in range(columns + 1):
            u = col / columns
            inner = 0.09 + t * 0.02
            outer = 0.46 + t * 1.07
            x = side * (inner + (outer - inner) * u)
            y = (-0.42 - 0.28 * t - 0.10 * math.sin(u * math.pi * 4 + t * 0.7) * t
                 - 0.038 * math.sin(u * math.pi * 10) * t * t)
            hem = (0.15 + 0.045 * math.sin(col * 2.7)
                   + (0.16 if col % 7 == 2 else 0)
                   + (0.11 if col % 9 == 5 else 0)
                   + (0.08 if col in (0, columns) else 0))
            z = 2.53 * (1 - t) + hem * t
            front.append((x, y, z))
    front_count = len(front)
    vertices = front + [(x, y - 0.018, z) for x, y, z in front]
    faces = []
    for row in range(rows):
        for col in range(columns):
            a, b = row * (columns + 1) + col, row * (columns + 1) + col + 1
            c, d = a + columns + 1, b + columns + 1
            faces.extend(((a, c, b), (b, c, d),
                          (front_count + a, front_count + b, front_count + c),
                          (front_count + b, front_count + d, front_count + c)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Mantle weave projection")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            point = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (point.x * 0.8, point.z * 0.8)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat, parent)


def cape_center_panel(name, side, mat, parent):
    """Deep overlapping cloth fills the open center behind the outer mantle."""
    columns, rows = 10, 16
    front = []
    for row in range(rows + 1):
        t = row / rows
        for col in range(columns + 1):
            u = col / columns
            x = side * (0.015 + u * (0.50 + t * 0.18))
            y = (-0.62 - t * 0.21
                 - 0.065 * math.sin(u * math.pi * 3 + t * 1.2) * t)
            hem = (0.16 + 0.075 * math.sin(col * 2.3 + (1 if side > 0 else 0))
                   + (0.11 if col in (2, 7) else 0))
            z = 2.46 * (1 - t) + hem * t
            front.append((x, y, z))
    count = len(front)
    mesh = bpy.data.meshes.new(name)
    vertices = front + [(x, y - 0.017, z) for x, y, z in front]
    faces = []
    for row in range(rows):
        for col in range(columns):
            a, b = row * (columns + 1) + col, row * (columns + 1) + col + 1
            c, d = a + columns + 1, b + columns + 1
            faces.extend(((a, c, b), (b, c, d),
                          (count + a, count + b, count + c),
                          (count + b, count + d, count + c)))
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Center mantle weave projection")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            point = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (point.x * 0.8, point.z * 0.8)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat, parent)


def mirror_outline(outline, side):
    return [(x * side, z) for x, z in outline]


def trim(name, points, radius, mat, parent):
    for index, (a, b) in enumerate(zip(points, points[1:])):
        rod(f"{name} {index}", a, b, radius, mat, parent, 8)


def faceted_orb(name, center, scale, mat, parent, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=center)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, parent)


# Worn, reflective tile modules. The center remains unobstructed for movement.
for ix in range(-5, 6):
    for iy in range(-5, 6):
        x, y = ix * 1.38, iy * 1.38
        wet = random.random() < 0.48
        box("cathedral floor slab", (x, y, -0.16 + random.random() * 0.018),
            (1.34, 1.34, 0.29), stone if wet else stone_dark, arena, 0.035)
        if (ix + 2 * iy) % 9 == 0:
            box("inlaid brass drain", (x, y, 0.009), (0.95, 0.035, 0.015), gold, arena, 0.005,
                (0, 0, math.pi / 4))
        if (ix * 7 + iy) % 13 == 0:
            box("small circuit seam", (x + 0.45, y - 0.43, 0.009),
                (0.24, 0.018, 0.014), cyan, arena, 0.004)

for side in (-1, 1):
    x = side * 7.6
    for y in (-6.5, -2.8, 0.9, 4.6):
        box("pier base", (x, y, 0.22), (1.02, 1.05, 0.45), wall, arena)
        box("pier shaft", (x, y, 1.93), (0.66, 0.72, 3.2), wall, arena, 0.065)
        box("pier capital", (x, y, 3.62), (1.1, 1.12, 0.32), gold, arena, 0.035)
        rod("vertical lumen", (x - side * 0.36, y + 0.37, 0.55),
            (x - side * 0.36, y + 0.37, 3.38), 0.021, cyan, arena, 8)
for x in (-5.6, -2.8, 0, 2.8, 5.6):
    box("rear wall buttress", (x, -7.5, 2.05), (0.48, 0.57, 4.1), wall, arena, 0.06)
    for side in (-1, 1):
        rod("pointed gothic arch", (x, -7.42, 3.47),
            (x + side * 1.36, -7.42, 4.68), 0.11, steel_dark, arena)
        rod("brass tracery", (x, -7.3, 3.5),
            (x + side * 1.28, -7.3, 4.61), 0.021, gold, arena, 8)
    box("stained dark glass", (x, -7.62, 2.75), (2.35, 0.04, 1.45), steel_dark, arena, 0.02)
    box("glass light slit", (x, -7.58, 2.73), (0.065, 0.05, 1.36), cyan, arena, 0.01)

# The display relic gives the materials an in-world light source.
cyl("relic pedestal", (-3.2, -1.7, 0.43), 0.88, 0.86, steel_dark, arena, 24)
cyl("pedestal brass rim", (-3.2, -1.7, 0.86), 0.96, 0.07, gold, arena, 24)
cone("floating oath crystal", (-3.2, -1.7, 1.51), 0.36, 0.0, 0.92, cyan, arena, 8)
cone("lower crystal point", (-3.2, -1.7, 0.99), 0.31, 0.0, 0.52, cyan, arena, 8,
     (math.pi, 0, 0))

# The oath knight follows the concept art's strong gold/black silhouette. Fine
# shapes are geometry so the same asset reads at close and medium camera ranges.
box("torso underplate", (0, -0.045, 2.13), (1.03, 0.56, 0.99), steel_dark, hero, 0.15)
box("waist seal", (0, -0.02, 1.61), (0.82, 0.45, 0.27), steel_dark, hero, 0.055)
cut_plate("cuirass outer shell", [(-0.47, 2.59), (0.47, 2.59), (0.61, 2.40),
    (0.52, 2.09), (0.32, 1.89), (0, 1.78), (-0.32, 1.89), (-0.52, 2.09),
    (-0.61, 2.40)], 0.37, 0.22, gold, hero, 0.035, crown=0.045)
cut_plate("cuirass recessed face", [(-0.43, 2.53), (0.43, 2.53), (0.54, 2.37),
    (0.45, 2.10), (0.27, 1.94), (0, 1.86), (-0.27, 1.94), (-0.45, 2.10),
    (-0.54, 2.37)], 0.44, 0.045, steel_dark, hero, 0.012)
for side in (-1, 1):
    cut_plate("split pectoral armor", mirror_outline([(0.08, 2.50), (0.42, 2.49),
        (0.53, 2.35), (0.41, 2.17), (0.19, 2.13), (0.075, 2.32)], side),
        0.50, 0.08, graphite, hero, 0.025, crown=0.08)
    cut_plate("raised collar lip", mirror_outline([(0.06, 2.58), (0.48, 2.59),
        (0.58, 2.48), (0.42, 2.51), (0.12, 2.54)], side),
        0.55, 0.055, gold, hero, 0.008)
    trim("cuirass etched line", [(side * 0.16, 0.585, 2.44),
        (side * 0.32, 0.585, 2.37), (side * 0.40, 0.585, 2.28)],
        0.012, steel_light, hero)
cut_plate("core dark socket", [(-0.21, 2.27), (0, 2.41), (0.21, 2.27),
    (0.18, 2.07), (0, 1.98), (-0.18, 2.07)], 0.59, 0.055, steel_dark, hero)
cyl("oath core dark well", (0, 0.65, 2.20), 0.165, 0.035,
    steel_dark, hero, 24, (math.pi / 2, 0, 0))
ring("oath core engraved brass bezel", (0, 0.681, 2.20), 0.168,
     0.022, gold, hero)
cyl("oath core cyan lens", (0, 0.695, 2.20), 0.106, 0.018,
    cyan, hero, 24, (math.pi / 2, 0, 0))
ring("oath core inner polished halo", (0, 0.712, 2.20), 0.10,
     0.010, steel_light, hero)
for side in (-1, 1):
    trim("branching cuirass circuit", [(side * 0.12, 0.604, 2.09),
        (side * 0.25, 0.604, 2.04), (side * 0.39, 0.604, 2.12)],
        0.008, cyan, hero)
    trim("collar inscribed runnel", [(side * 0.10, 0.568, 2.55),
        (side * 0.31, 0.568, 2.54), (side * 0.46, 0.568, 2.49)],
        0.008, gold, hero)
    cut_plate("lower pectoral nested rib", mirror_outline([(0.18, 2.13),
        (0.41, 2.17), (0.49, 2.08), (0.31, 2.02), (0.18, 2.06)], side),
        0.59, 0.035, graphite, hero, 0.006, crown=0.025)
    trim("sternum engraved brass strut", [(side * 0.14, 0.65, 2.37),
        (side * 0.20, 0.65, 2.30), (side * 0.17, 0.65, 2.19)],
        0.007, gold, hero)
    cut_plate("cuirass raised clavicle insert", mirror_outline([(0.13, 2.57),
        (0.46, 2.56), (0.53, 2.46), (0.38, 2.45), (0.21, 2.49)], side),
        0.60, 0.027, steel_dark, hero, 0.008, crown=0.018)
    trim("cuirass engraved clavicle lip", [(side * 0.16, 0.625, 2.54),
        (side * 0.40, 0.625, 2.54), (side * 0.49, 0.625, 2.47)],
        0.009, gold, hero)
    cut_plate("pectoral forged wing", mirror_outline([(0.24, 2.42),
        (0.42, 2.41), (0.45, 2.32), (0.33, 2.24), (0.23, 2.29)], side),
        0.625, 0.019, graphite, hero, 0.007, crown=0.013)
for level in range(3):
    z = 1.84 - level * 0.13
    cut_plate("overlapping abdominal lamella", [(-0.37 + level * 0.04, z + 0.08),
        (0.37 - level * 0.04, z + 0.08), (0.30 - level * 0.03, z - 0.045),
        (0, z - 0.083), (-0.30 + level * 0.03, z - 0.045)],
        0.47 + level * 0.014, 0.055, gold if level == 2 else graphite, hero, 0.014)
    trim("abdominal plate engraved lip", [(-0.27 + level * 0.025,
        0.515 + level * 0.014, z + 0.05),
        (0, 0.515 + level * 0.014, z + 0.025),
        (0.27 - level * 0.025, 0.515 + level * 0.014, z + 0.05)],
        0.007, gold, hero)
cut_plate("sternum descending forged keel", [(-0.055, 2.10),
    (0.055, 2.10), (0.105, 1.94), (0, 1.83), (-0.105, 1.94)],
    0.60, 0.026, steel_dark, hero, 0.008, crown=0.017)
trim("sternum gold engraving", [(0, 0.637, 2.07),
    (0, 0.637, 1.92), (0.075, 0.637, 1.86)], 0.008, gold, hero)
cut_plate("belt buckle", [(-0.17, 1.69), (0.17, 1.69), (0.20, 1.49),
    (0, 1.43), (-0.20, 1.49)], 0.49, 0.067, gold, hero)
cut_plate("belt circuit", [(-0.065, 1.65), (0.065, 1.65), (0.08, 1.53),
    (0, 1.49), (-0.08, 1.53)], 0.55, 0.022, cyan, hero, 0.005)
for side in (-1, 1):
    cut_plate("split battle fauld", mirror_outline([(0.21, 1.54), (0.47, 1.57),
        (0.51, 1.24), (0.40, 1.08), (0.18, 1.21)], side),
        0.34, 0.11, steel_dark, hero, 0.025)
    trim("fauld gold piped hem", [(side * 0.19, 0.36, 1.21),
        (side * 0.39, 0.36, 1.07), (side * 0.50, 0.36, 1.23)],
        0.015, gold, hero)

for side in (-1, 1):
    x = side * 0.305
    rod("leg black articulated spine", (x, -0.035, 1.47),
        (x, -0.035, 0.35), 0.150, steel_dark, hero)
    faceted_orb("open knee articulation", (x, 0.05, 1.00),
                (0.21, 0.21, 0.18), steel_dark, hero)
    cut_plate("tapered thigh shell", mirror_outline([(0.13, 1.56), (0.44, 1.54),
        (0.51, 1.29), (0.43, 1.08), (0.17, 1.08), (0.10, 1.30)], side),
        0.255, 0.30, graphite, hero, 0.035, crown=0.07)
    cut_plate("thigh bevel highlight", mirror_outline([(0.16, 1.50), (0.40, 1.49),
        (0.44, 1.32), (0.33, 1.19), (0.19, 1.22)], side),
        0.304, 0.04, steel_dark, hero, 0.009)
    cut_plate("thigh forged inset spine", mirror_outline([(0.23, 1.46),
        (0.39, 1.42), (0.37, 1.28), (0.30, 1.17),
        (0.22, 1.26)], side), 0.346, 0.024, graphite, hero,
        0.006, crown=0.023)
    trim("thigh brass forged outline", [(side * 0.15, 0.315, 1.48),
        (side * 0.42, 0.315, 1.46), (side * 0.45, 0.315, 1.30),
        (side * 0.36, 0.315, 1.16)], 0.012, gold, hero)
    trim("thigh etched split line", [(side * 0.28, 0.355, 1.43),
        (side * 0.31, 0.355, 1.33), (side * 0.37, 0.355, 1.27)],
        0.008, steel_dark, hero)
    cut_plate("pointed knee cup", mirror_outline([(0.30, 1.10), (0.45, 1.02),
        (0.30, 0.91), (0.15, 1.02)], side),
        0.36, 0.08, graphite, hero, 0.022, crown=0.025)
    trim("knee brass forged edging", [(side * 0.30, 0.394, 1.10),
        (side * 0.45, 0.394, 1.02), (side * 0.30, 0.394, 0.91),
        (side * 0.15, 0.394, 1.02), (side * 0.30, 0.394, 1.10)],
        0.009, gold, hero)
    cut_plate("knee center", mirror_outline([(0.30, 1.07), (0.38, 1.02),
        (0.30, 0.96), (0.22, 1.02)], side),
        0.42, 0.028, steel_dark, hero, 0.007)
    faceted_orb("knee side hinge", (side * 0.43, 0.09, 1.02),
                (0.055, 0.055, 0.055), steel_dark, hero, 2)
    faceted_orb("knee side hinge axle", (side * 0.468, 0.10, 1.02),
                (0.020, 0.020, 0.020), gold, hero, 2)
    cut_plate("sloped greave", mirror_outline([(0.16, 0.90), (0.43, 0.89),
        (0.48, 0.69), (0.40, 0.33), (0.22, 0.29), (0.12, 0.57)], side),
        0.27, 0.31, graphite, hero, 0.028, crown=0.065)
    trim("greave cyan filament", [(side * 0.29, 0.309, 0.78),
        (side * 0.30, 0.316, 0.57), (side * 0.34, 0.313, 0.42)],
        0.014, cyan, hero)
    for rivet_z in (0.72, 0.47):
        faceted_orb("greave anchor rivet", (side * 0.43, 0.31, rivet_z),
                    (0.018, 0.014, 0.018), gold, hero)
    cut_plate("greave raised forged keel", mirror_outline([(0.29, 0.83),
        (0.38, 0.69), (0.36, 0.43), (0.31, 0.34), (0.27, 0.45),
        (0.25, 0.69)], side), 0.365, 0.025, steel_dark, hero, 0.008,
        crown=0.020)
    trim("greave engraving inner gold", [(side * 0.19, 0.348, 0.80),
        (side * 0.15, 0.348, 0.59), (side * 0.24, 0.348, 0.37)],
        0.008, gold, hero,)
    box("articulated heel", (x, -0.10, 0.18), (0.31, 0.40, 0.22),
        steel_dark, hero, 0.035)
    cut_plate("pointed sabaton", mirror_outline([(0.16, 0.37), (0.42, 0.36),
        (0.46, 0.21), (0.41, 0.065), (0.20, 0.065), (0.14, 0.21)], side),
        0.51, 0.22, graphite, hero, 0.020, crown=0.035)
    cut_plate("sabatons angular toe crest", mirror_outline([(0.20, 0.28),
        (0.38, 0.28), (0.43, 0.16), (0.32, 0.12), (0.17, 0.16)], side),
        0.565, 0.035, steel_dark, hero, 0.008, crown=0.019)
    trim("sabatons inset toe arris", [(side * 0.18, 0.59, 0.21),
        (side * 0.31, 0.59, 0.13), (side * 0.43, 0.59, 0.19)],
        0.010, gold, hero)
    for step in range(2):
        z = 0.20 - step * 0.07
        rod("boot toe separation", (side * 0.18, 0.526, z),
            (side * 0.47, 0.526, z), 0.01, gold, hero, 6)

for side in (-1, 1):
    x = side * 0.79
    rod("upper arm under-suit", (x, -0.04, 2.43),
        (x + side * 0.045, 0.005, 1.84), 0.16, steel_dark, hero)
    faceted_orb("elbow hinge", (x + side * 0.03, 0.02, 1.84),
                (0.18, 0.20, 0.18), steel_dark, hero)
    cut_plate("swept upper pauldron", mirror_outline([(0.50, 2.61), (0.81, 2.75),
        (1.03, 2.69), (1.19, 2.51), (1.08, 2.36), (0.73, 2.38),
        (0.54, 2.48)], side), 0.295, 0.38, graphite, hero, 0.027, crown=0.06)
    cut_plate("inset shoulder facet", mirror_outline([(0.62, 2.57), (0.82, 2.68),
        (1.03, 2.62), (1.11, 2.51), (0.98, 2.43), (0.74, 2.46)], side),
        0.355, 0.052, steel_dark, hero, 0.009, crown=0.075)
    trim("pauldron upper forged brass rim", [(side * 0.51, 0.38, 2.62),
        (side * 0.81, 0.38, 2.75), (side * 1.03, 0.38, 2.69),
        (side * 1.18, 0.38, 2.52)], 0.021, gold, hero)
    trim("pauldron hanging brass rim", [(side * 0.74, 0.29, 2.37),
        (side * 1.07, 0.29, 2.36), (side * 1.01, 0.29, 2.20)],
        0.014, gold, hero)
    cut_plate("hanging pauldron lame", mirror_outline([(0.72, 2.38),
        (1.06, 2.37), (1.00, 2.21), (0.75, 2.19)], side),
        0.22, 0.29, steel, hero, 0.023)
    cut_plate("upper arm scale", mirror_outline([(0.70, 2.19), (0.94, 2.18),
        (0.93, 1.92), (0.80, 1.86), (0.68, 1.96)], side),
        0.23, 0.20, graphite, hero, 0.02)
    cut_plate("faceted forearm vambrace", mirror_outline([(0.72, 1.89),
        (0.98, 1.85), (1.03, 1.55), (0.89, 1.39), (0.72, 1.48)], side),
        0.29, 0.25, graphite, hero, 0.027, crown=0.055)
    trim("forearm circuit channel", [(side * 0.86, 0.34, 1.79),
        (side * 0.90, 0.34, 1.61), (side * 0.86, 0.34, 1.50)],
        0.012, cyan, hero)
    faceted_orb("gauntlet fingers and grip", (x + side * 0.10, 0.10, 1.36),
                (0.15, 0.19, 0.17), graphite, hero)
    for finger in range(3):
        fx = x + side * (0.045 + finger * 0.062)
        box("separate articulated finger", (fx, 0.25, 1.30),
            (0.045, 0.09, 0.16), steel_dark, hero, 0.012)
        box("brass finger knuckle", (fx, 0.30, 1.35),
            (0.050, 0.025, 0.035), gold, hero, 0.006)
    trim("pauldron internal circuit", [(side * 0.76, 0.415, 2.56),
        (side * 0.88, 0.415, 2.58), (side * 1.00, 0.415, 2.53)],
        0.010, cyan, hero)
    for rivet_z in (2.55, 2.45):
        faceted_orb("shoulder brass rivet", (side * 0.99, 0.385, rivet_z),
                    (0.022, 0.017, 0.022), steel_light, hero)
    cut_plate("shoulder inset forged rosette", mirror_outline([(0.76, 2.60),
        (0.90, 2.64), (1.06, 2.58), (1.02, 2.50), (0.84, 2.51)], side),
        0.465, 0.022, graphite, hero, 0.009, crown=0.018)
    trim("shoulder layered gold arris", [(side * 0.72, 0.491, 2.60),
        (side * 0.87, 0.491, 2.65), (side * 1.09, 0.491, 2.56)],
        0.010, gold, hero)
    faceted_orb("shoulder central stamped fastener", (side * 0.91, 0.502, 2.58),
                (0.034, 0.017, 0.034), gold, hero, 2)
    cut_plate("vambrace tendon ridge", mirror_outline([(0.85, 1.84),
        (0.94, 1.76), (0.94, 1.59), (0.88, 1.48), (0.82, 1.59)], side),
        0.355, 0.027, steel_dark, hero, 0.008, crown=0.016)
    trim("vambrace brass split", [(side * 0.83, 0.374, 1.80),
        (side * 0.90, 0.374, 1.69), (side * 0.87, 0.374, 1.51)],
        0.008, gold, hero)

# The concept's helmet is tall, narrow and mostly black. It has two hairline
# cyan visor rays, not broad illuminated eyes or a bright gold mask.
box("helmet neck seal", (0, -0.06, 2.67), (0.42, 0.39, 0.22),
    steel_dark, hero, 0.05)
for level in range(3):
    z = 2.59 + level * 0.065
    rod("helmet ribbed collar", (-0.21 + level * 0.025, 0.20, z),
        (0.21 - level * 0.025, 0.20, z), 0.012, gold, hero, 8)
faceted_orb("helmet slim faceted shell", (0, -0.045, 3.06),
            (0.29, 0.29, 0.48), helmet_metal, hero, 2)
faceted_orb("helmet inner black socket", (0, 0.20, 3.02),
            (0.225, 0.27, 0.37), visor_glass, hero, 2)
cut_plate("helmet recessed shadow visor", [(-0.25, 3.27), (0.25, 3.27),
    (0.23, 2.91), (0.13, 2.76), (0, 2.67), (-0.13, 2.76), (-0.23, 2.91)],
    0.325, 0.080, visor_glass, hero, 0.008, crown=0.020)
cut_plate("helmet pointed crown", [(-0.27, 3.30), (-0.19, 3.48),
    (0, 3.72), (0.19, 3.48), (0.27, 3.30), (0.09, 3.36),
    (0, 3.42), (-0.09, 3.36)], 0.255, 0.30, helmet_metal, hero,
    0.012, crown=0.045)
cut_plate("helmet central crown facet", [(-0.105, 3.39), (0, 3.66),
    (0.105, 3.39), (0.045, 3.31), (0, 3.29), (-0.045, 3.31)],
    0.345, 0.045, helmet_metal, hero, 0.006, crown=0.025)
trim("helmet crown hairline gold", [(-0.13, 0.376, 3.43),
    (0, 0.376, 3.65), (0.13, 0.376, 3.43)], 0.006, gold, hero)
for side in (-1, 1):
    cut_plate("helmet narrow brow wing", mirror_outline([(0.16, 3.27),
        (0.27, 3.28), (0.245, 3.17), (0.19, 3.14)], side),
        0.408, 0.030, steel_dark, hero, 0.004)
    trim("helmet brow hairline", [(side * 0.18, 0.448, 3.25),
        (side * 0.25, 0.448, 3.27)], 0.004, gold, hero)
for side in (-1, 1):
    cut_plate("helmet inset visor slit shadow", mirror_outline([(0.085, 3.31),
        (0.132, 3.30), (0.158, 3.14), (0.144, 3.07),
        (0.108, 3.11)], side), 0.345, 0.018, visor_glass, hero, 0.003)
    cut_plate("helmet cyan recessed slit", mirror_outline([(0.100, 3.29),
        (0.112, 3.29), (0.143, 3.14), (0.135, 3.095),
        (0.121, 3.13)], side), 0.405, 0.010, visor_cyan, hero, 0.002)
    cut_plate("helmet inner slit lip", mirror_outline([(0.064, 3.29),
        (0.090, 3.31), (0.110, 3.12), (0.092, 3.06),
        (0.071, 3.16)], side), 0.443, 0.025, helmet_metal, hero,
        0.004, crown=0.009)
    cut_plate("helmet outer slit lip", mirror_outline([(0.140, 3.29),
        (0.190, 3.28), (0.205, 3.16), (0.172, 3.04),
        (0.153, 3.11)], side), 0.443, 0.027, helmet_metal, hero,
        0.004, crown=0.011)
    cut_plate("helmet lower face wing", mirror_outline([(0.094, 3.04),
        (0.17, 3.03), (0.198, 2.89), (0.10, 2.79),
        (0.060, 2.87)], side), 0.432, 0.030, helmet_metal, hero,
        0.004, crown=0.010)
    trim("helmet slit outer hairline", [(side * 0.180, 0.463, 3.24),
        (side * 0.185, 0.463, 3.16),
        (side * 0.17, 0.463, 3.09)], 0.003, gold, hero)
    cut_plate("helmet upper cheek armor", mirror_outline([(0.205, 3.19),
        (0.275, 3.16), (0.30, 3.01), (0.26, 2.95),
        (0.225, 3.03)], side), 0.395, 0.060, helmet_metal, hero,
        0.007, crown=0.018)
    cut_plate("helmet lower cheek lamella", mirror_outline([(0.23, 3.00),
        (0.28, 2.97), (0.245, 2.81), (0.19, 2.78),
        (0.205, 2.90)], side), 0.418, 0.035, steel_dark, hero,
        0.005, crown=0.010)
    side_plate("helmet continuous cheek shell",
        [(-0.25, 3.29), (-0.11, 3.44), (0.11, 3.42),
         (0.34, 3.20), (0.40, 3.03), (0.34, 2.87),
         (0.10, 2.80), (-0.23, 2.90)], side, 0.255, 0.040,
        helmet_metal, hero)
    side_plate("helmet nested temple facet",
        [(-0.13, 3.27), (-0.04, 3.37), (0.10, 3.33),
         (0.28, 3.16), (0.32, 3.04), (0.17, 2.92),
         (-0.07, 3.00)], side, 0.302, 0.025, helmet_metal, hero)
    trim("helmet side forged arris", [
        (side * 0.270, -0.21, 3.30),
        (side * 0.270, -0.09, 3.41),
        (side * 0.270, 0.09, 3.39)], 0.005, gold, hero)
    trim("helmet side inset hairline", [
        (side * 0.350, -0.11, 3.27),
        (side * 0.350, -0.03, 3.34),
        (side * 0.350, 0.08, 3.30),
        (side * 0.350, 0.24, 3.15)], 0.005, gold, hero)
    trim("helmet cheek restrained gold edge", [(side * 0.265, 0.457, 3.17),
        (side * 0.294, 0.457, 3.01),
        (side * 0.24, 0.457, 2.83)], 0.005, gold, hero)
    cut_plate("helmet needle temple spine", mirror_outline([(0.28, 3.35),
        (0.315, 3.56), (0.345, 3.28), (0.30, 3.08)], side),
        0.075, 0.14, helmet_metal, hero, 0.006, crown=0.017)
    trim("helmet temple fine arris", [(side * 0.31, 0.10, 3.54),
        (side * 0.325, 0.10, 3.30),
        (side * 0.30, 0.10, 3.10)], 0.006, gold, hero)
    faceted_orb("helmet temple micro lock", (side * 0.292, 0.22, 3.18),
                (0.018, 0.012, 0.018), gold, hero, 2)
cut_plate("helmet sculpted nasal keel", [(-0.055, 3.29),
    (0.055, 3.29), (0.062, 3.14), (0.052, 2.91),
    (0, 2.83), (-0.052, 2.91), (-0.062, 3.14)],
    0.444, 0.024, helmet_metal, hero, 0.004, crown=0.012)
cut_plate("helmet nasal recessed arris", [(-0.014, 3.24),
    (0.014, 3.24), (0.019, 2.98), (0, 2.90), (-0.019, 2.98)],
    0.462, 0.010, visor_glass, hero, 0.002)
cut_plate("helmet pointed chin jaw", [(-0.15, 2.84), (0, 2.79),
    (0.15, 2.84), (0.090, 2.74), (0, 2.68), (-0.090, 2.74)],
    0.405, 0.045, helmet_metal, hero, 0.005)
cut_plate("helmet rear segmented crown", [(-0.27, 3.39), (0, 3.68),
    (0.27, 3.39), (0.26, 2.92), (0.13, 2.77),
    (-0.13, 2.77), (-0.26, 2.92)],
    -0.365, 0.095, steel_dark, hero, 0.014)
trim("helmet rear crown gold peak", [(-0.25, -0.47, 3.37),
    (0, -0.47, 3.65), (0.25, -0.47, 3.37)], 0.008, gold, hero)
for side in (-1, 1):
    trim("helmet rear cheek seam", [(side * 0.24, -0.478, 3.31),
        (side * 0.21, -0.478, 3.04),
        (side * 0.11, -0.478, 2.86)], 0.008, gold, hero)
    for vent in range(3):
        z = 3.04 - vent * 0.045
        rod("helmet rear nape vent", (side * 0.065, -0.48, z),
            (side * 0.18, -0.48, z), 0.006, gold, hero, 6)
cut_plate("helmet rear nape circuit", [(-0.025, 3.25), (0.025, 3.25),
    (0.050, 2.98), (0, 2.90), (-0.050, 2.98)],
    -0.49, 0.010, visor_cyan, hero, 0.003)

# Keep the carved silhouette close to the concept's head-to-shoulder ratio.
# The geometry is scaled before rig binding and before source/cage separation.
from mathutils import Matrix
face_layers = (
    "recessed shadow visor", "narrow brow wing", "brow hairline",
    "inset visor slit shadow", "cyan recessed slit", "inner slit lip",
    "outer slit lip", "lower face wing", "slit outer hairline",
    "sculpted nasal keel", "nasal recessed arris", "upper cheek armor",
    "lower cheek lamella", "cheek restrained gold edge",
    "pointed chin jaw",
)
helmet_fit = (Matrix.Translation((0, 0, 2.72))
              @ Matrix.Diagonal((0.82, 0.83, 0.76, 1))
              @ Matrix.Translation((0, 0, -2.72)))
for part in hero.children:
    if part.type == "MESH" and part.name.startswith("helmet"):
        forward = (Matrix.Translation((0, 0.14, 0))
                   if any(term in part.name for term in face_layers)
                   else Matrix.Identity(4))
        part.matrix_world = helmet_fit @ forward @ part.matrix_world

# Rear view matches the concept's broad torn mantle and visible cyan reactor.
cape_center_panel("left cape center underlay", -1, cloth, hero)
cape_center_panel("right cape center underlay", 1, cloth, hero)
cape_panel("left sweeping mantle", -1, cloth, hero)
cape_panel("right sweeping mantle", 1, cloth, hero)
for side in (-1, 1):
    fold("cape outer dark fold", [(side * 0.40, -0.29, 2.43),
        (side * 0.67, -0.44, 1.47), (side * 0.79, -0.67, 0.21),
        (side * 0.57, -0.82, 0.38), (side * 0.51, -0.72, 1.61)],
        steel_dark, hero, 0.018)
    trim("cape long cyan seam", [(side * 0.23, -0.72, 1.64),
        (side * 0.29, -0.84, 1.00), (side * 0.37, -0.87, 0.38)],
        0.018, cyan_thread, hero)
    trim("mantle shoulder piping", [(side * 0.08, -0.39, 2.48),
        (side * 0.43, -0.28, 2.58), (side * 0.66, -0.48, 1.43)],
        0.018, gold, hero)
    fold("cape inner shadow pleat", [(side * 0.15, -0.55, 1.87),
        (side * 0.30, -0.81, 1.48), (side * 0.43, -0.91, 0.39),
        (side * 0.27, -0.94, 0.26), (side * 0.10, -0.77, 1.35)],
        steel_dark, hero, 0.014)
    trim("cape branching woven circuit", [(side * 0.29, -0.86, 1.01),
        (side * 0.46, -0.87, 0.83), (side * 0.52, -0.85, 0.59)],
        0.012, cyan_thread, hero)
    trim("cape hem metal thread", [(side * 0.13, -0.91, 0.29),
        (side * 0.37, -0.87, 0.39), (side * 0.73, -0.70, 0.22)],
        0.015, gold, hero)
    trim("mantle outer luminous seam", [(side * 0.46, -0.45, 2.35),
        (side * 0.61, -0.53, 1.75), (side * 0.96, -0.69, 0.96),
        (side * 1.31, -0.71, 0.35)], 0.013, cyan_thread, hero)
fold("short armored mantle collar", [(-0.54, -0.29, 2.55),
    (0.54, -0.29, 2.55), (0.57, -0.59, 2.40),
    (0.20, -0.65, 2.34), (0, -0.68, 2.37),
    (-0.20, -0.65, 2.34), (-0.57, -0.59, 2.40)],
    cloth, hero, 0.07)
trim("upper mantle collar edge", [(-0.53, -0.60, 2.40),
    (-0.18, -0.67, 2.35), (0, -0.70, 2.37),
    (0.18, -0.67, 2.35), (0.53, -0.60, 2.40)],
    0.020, gold, hero)
box("reactor armored backpack", (0, -0.46, 2.17),
    (0.46, 0.30, 0.60), steel_dark, hero, 0.065)
cyl("back circular reactor casing", (0, -0.66, 2.21),
    0.21, 0.08, gold, hero, 16, (math.pi / 2, 0, 0))
cyl("back reactor light", (0, -0.715, 2.21),
    0.13, 0.035, cyan, hero, 16, (math.pi / 2, 0, 0))
for side in (-1, 1):
    rod("reactor side conduit", (side * 0.19, -0.68, 2.33),
        (side * 0.27, -0.67, 2.52), 0.022, cyan, hero, 8)

# A pointed kite shield and a flat, tapered sword keep readable equipment
# silhouettes at game distance; each has raised inlay at inspection distance.
shield_shape = [(-1.22, 2.37), (-0.69, 2.24), (-0.69, 1.70),
    (-0.91, 1.23), (-1.22, 0.94), (-1.53, 1.23),
    (-1.75, 1.70), (-1.75, 2.24)]
cut_plate("shield gold perimeter", shield_shape, 0.58, 0.15, gold, hero, 0.035)
cut_plate("shield reverse graphite shell", [(-1.22, 2.30), (-0.76, 2.18),
    (-0.76, 1.72), (-0.95, 1.26), (-1.22, 1.03),
    (-1.49, 1.26), (-1.68, 1.72), (-1.68, 2.18)],
    0.414, 0.045, steel_dark, hero, 0.010)
for side in (-1, 1):
    trim("shield reverse diagonal brass brace", [
        (-1.22 + side * 0.34, 0.358, 2.12),
        (-1.22 + side * 0.12, 0.358, 1.82),
        (-1.22 + side * 0.07, 0.358, 1.24)],
        0.012, gold, hero)
rod("shield reverse center steel rib", (-1.22, 0.352, 2.14),
    (-1.22, 0.352, 1.20), 0.015, steel, hero, 8)
cut_plate("shield dark beveled field", [(-1.22, 2.29), (-0.78, 2.18),
    (-0.78, 1.72), (-0.97, 1.28), (-1.22, 1.06),
    (-1.47, 1.28), (-1.66, 1.72), (-1.66, 2.18)],
    0.635, 0.05, graphite, hero, 0.025, crown=0.055)
cut_plate("shield central recessed spine", [(-1.27, 2.25), (-1.17, 2.25),
    (-1.12, 1.71), (-1.22, 1.24), (-1.32, 1.71)],
    0.69, 0.04, steel_dark, hero, 0.01)
cut_plate("shield cyan oath glyph", [(-1.245, 2.12), (-1.18, 2.12),
    (-1.18, 1.65), (-1.22, 1.49), (-1.26, 1.65)],
    0.737, 0.018, cyan, hero, 0.004)
cyl("shield round socket", (-1.22, 0.754, 1.96), 0.15, 0.023,
    steel_dark, hero, 24, (math.pi / 2, 0, 0))
ring("shield round brass setting", (-1.22, 0.777, 1.96), 0.15,
     0.019, gold, hero)
cyl("shield round cyan emitter", (-1.22, 0.786, 1.96), 0.068, 0.016,
    cyan, hero, 24, (math.pi / 2, 0, 0))
for side in (-1, 1):
    cut_plate("shield upper chevron", [(-1.22, 2.08),
        (-1.22 + side * 0.29, 2.02), (-1.22 + side * 0.20, 1.96),
        (-1.22, 2.01)], 0.70, 0.028, gold, hero, 0.006)
    trim("shield branching oath trace", [(-1.22, 0.756, 1.86),
        (-1.22 + side * 0.12, 0.756, 1.69),
        (-1.22 + side * 0.19, 0.756, 1.50)],
        0.008, visor_cyan, hero)
    for z in (1.44, 1.58, 1.73):
        faceted_orb("shield edge fastener", (-1.22 + side * 0.39,
                    0.679, z), (0.019, 0.015, 0.019),
                    steel_light, hero)
    cut_plate("shield swept upper segmented fluting", [
        (-1.22 + side * 0.09, 2.24), (-1.22 + side * 0.39, 2.15),
        (-1.22 + side * 0.35, 1.98), (-1.22 + side * 0.23, 2.04),
        (-1.22 + side * 0.12, 2.10)],
        0.731, 0.029, steel_dark, hero, 0.007, crown=0.016)
    trim("shield upper inset gold arris", [
        (-1.22 + side * 0.11, 0.765, 2.23),
        (-1.22 + side * 0.39, 0.765, 2.15),
        (-1.22 + side * 0.34, 0.765, 1.99)],
        0.010, gold, hero)
    cut_plate("shield lower forged wing", [
        (-1.22 + side * 0.12, 1.59), (-1.22 + side * 0.34, 1.63),
        (-1.22 + side * 0.24, 1.33), (-1.22 + side * 0.05, 1.18),
        (-1.22 + side * 0.19, 1.43)],
        0.727, 0.030, steel_dark, hero, 0.007, crown=0.014)
    trim("shield lower gold arris", [
        (-1.22 + side * 0.35, 0.762, 1.64),
        (-1.22 + side * 0.25, 0.762, 1.34),
        (-1.22 + side * 0.07, 0.762, 1.17)],
        0.010, gold, hero)
rod("sword leather-wrapped grip", (1.22, 0.18, 1.46),
    (1.22, 0.18, 1.86), 0.050, steel_dark, hero)
for index in range(5):
    z = 1.51 + index * 0.068
    rod("sword grip winding", (1.177, 0.226, z),
        (1.263, 0.226, z + 0.026), 0.008, gold, hero, 6)
    rod("sword reverse grip winding", (1.177, 0.124, z + 0.026),
        (1.263, 0.124, z), 0.008, gold, hero, 6)
cut_plate("sword pommel gold silhouette", [(1.13, 1.82), (1.31, 1.82),
    (1.31, 1.91), (1.22, 2.04), (1.13, 1.91)],
    0.28, 0.07, gold, hero, 0.012)
cut_plate("sword pommel dark inset", [(1.17, 1.86), (1.27, 1.86),
    (1.27, 1.91), (1.22, 1.98), (1.17, 1.91)],
    0.322, 0.014, steel_dark, hero, 0.005)
cut_plate("sword pommel cyan fleck", [(1.20, 1.89), (1.24, 1.89),
    (1.22, 1.94)], 0.345, 0.005, visor_cyan, hero, 0.001)
cut_plate("sword reverse pommel dark inset", [(1.17, 1.86),
    (1.27, 1.86), (1.27, 1.91), (1.22, 1.98), (1.17, 1.91)],
    0.204, 0.014, steel_dark, hero, 0.005)
cut_plate("sword reverse pommel cyan fleck", [(1.20, 1.89),
    (1.24, 1.89), (1.22, 1.94)],
    0.182, 0.005, visor_cyan, hero, 0.001)

# A silver cutting edge surrounds a dark forged blade. Separate inset plates
# make the central glowing channel a recess instead of a light painted over
# the broad, flat white blade of the first iteration.
cut_plate("sword silver cutting edge", [(1.095, 1.44), (1.345, 1.44),
    (1.325, 0.35), (1.22, 0.04), (1.115, 0.35)],
    0.21, 0.085, steel, hero, 0.008)
cut_plate("sword reverse dark forged blade", [(1.112, 1.40),
    (1.328, 1.40), (1.307, 0.36), (1.22, 0.075), (1.133, 0.36)],
    0.120, 0.018, steel_dark, hero, 0.004)
cut_plate("sword dark forged blade", [(1.112, 1.40), (1.328, 1.40),
    (1.307, 0.36), (1.22, 0.075), (1.133, 0.36)],
    0.292, 0.025, steel_dark, hero, 0.004)
for side in (-1, 1):
    cut_plate("sword polished edge arris", [(1.22 + side * 0.125, 1.39),
        (1.22 + side * 0.108, 1.32),
        (1.22 + side * 0.100, 0.37),
        (1.22, 0.075),
        (1.22 + side * 0.111, 0.36)],
        0.319, 0.009, steel_light, hero, 0.002)
    trim("sword blade shoulder arris", [(1.22 + side * 0.10, 0.326, 1.40),
        (1.22 + side * 0.055, 0.326, 1.32)],
        0.007, gold, hero)
    trim("sword reverse shoulder arris", [(1.22 + side * 0.10, 0.079, 1.40),
        (1.22 + side * 0.055, 0.079, 1.32)],
        0.007, gold, hero)
cut_plate("blade smoked recessed channel", [(1.18, 1.30), (1.26, 1.30),
    (1.252, 0.38), (1.22, 0.22), (1.188, 0.38)],
    0.326, 0.013, visor_glass, hero, 0.002)
cut_plate("blade cyan inset channel", [(1.211, 1.23), (1.229, 1.23),
    (1.229, 0.42), (1.22, 0.29), (1.211, 0.42)],
    0.345, 0.007, visor_cyan, hero, 0.002)
cut_plate("blade reverse smoked channel", [(1.18, 1.30),
    (1.26, 1.30), (1.252, 0.38), (1.22, 0.22), (1.188, 0.38)],
    0.094, 0.013, visor_glass, hero, 0.002)
cut_plate("blade reverse cyan inset channel", [(1.211, 1.23),
    (1.229, 1.23), (1.229, 0.42), (1.22, 0.29), (1.211, 0.42)],
    0.073, 0.007, visor_cyan, hero, 0.002)
for side in (-1, 1):
    # Downturned forged quillons reproduce the recognizable split-wing guard
    # of the concept sword, with a brass arris and black recessed side plate.
    cut_plate("sword guard brass wing", [(1.22 + side * 0.08, 1.48),
        (1.22 + side * 0.23, 1.61), (1.22 + side * 0.31, 1.61),
        (1.22 + side * 0.27, 1.30), (1.22 + side * 0.15, 1.22),
        (1.22 + side * 0.19, 1.48)],
        0.278, 0.055, steel_dark, hero, 0.009)
    cut_plate("sword guard dark wing inset", [(1.22 + side * 0.16, 1.49),
        (1.22 + side * 0.255, 1.56), (1.22 + side * 0.265, 1.39),
        (1.22 + side * 0.18, 1.30),
        (1.22 + side * 0.22, 1.47)],
        0.338, 0.012, graphite, hero, 0.004)
    trim("sword guard cutline", [(1.22 + side * 0.14, 0.353, 1.49),
        (1.22 + side * 0.25, 0.353, 1.56),
        (1.22 + side * 0.26, 0.353, 1.37),
        (1.22 + side * 0.18, 0.353, 1.28)],
        0.008, gold, hero)
    cut_plate("sword reverse guard wing inset", [
        (1.22 + side * 0.16, 1.49),
        (1.22 + side * 0.255, 1.56),
        (1.22 + side * 0.265, 1.39),
        (1.22 + side * 0.18, 1.30),
        (1.22 + side * 0.22, 1.47)],
        0.213, 0.012, graphite, hero, 0.004)
    trim("sword reverse guard cutline", [
        (1.22 + side * 0.14, 0.190, 1.49),
        (1.22 + side * 0.25, 0.190, 1.56),
        (1.22 + side * 0.26, 0.190, 1.37),
        (1.22 + side * 0.18, 0.190, 1.28)],
        0.008, gold, hero)
cut_plate("sword ornate central quillon", [(1.08, 1.44),
    (1.22, 1.57), (1.36, 1.44), (1.22, 1.34)],
    0.350, 0.040, gold, hero, 0.008, crown=0.012)
cyl("sword black hilt socket", (1.22, 0.385, 1.46), 0.083, 0.018,
    steel_dark, hero, 24, (math.pi / 2, 0, 0))
ring("sword brass hilt setting", (1.22, 0.397, 1.46), 0.081,
     0.009, gold, hero)
cyl("sword cyan hilt gem", (1.22, 0.405, 1.46), 0.050, 0.016,
    visor_cyan, hero, 24, (math.pi / 2, 0, 0))
cut_plate("sword reverse ornate central quillon", [(1.08, 1.44),
    (1.22, 1.57), (1.36, 1.44), (1.22, 1.34)],
    0.179, 0.025, gold, hero, 0.008)
cyl("sword reverse black hilt socket", (1.22, 0.145, 1.46),
    0.083, 0.018, steel_dark, hero, 24, (math.pi / 2, 0, 0))
ring("sword reverse brass hilt setting", (1.22, 0.128, 1.46),
     0.081, 0.009, gold, hero)
cyl("sword reverse cyan hilt gem", (1.22, 0.116, 1.46),
    0.050, 0.016, visor_cyan, hero, 24, (math.pi / 2, 0, 0))

# Hostile: an insectoid, plated raptor instead of a second box-shaped person.
ex, ey = 2.55, -1.55
faceted_orb("enemy inner chassis", (ex, ey, 1.40),
            (0.54, 0.45, 0.83), obsidian, enemy, 1)
cut_plate("enemy chest carapace", [(ex - 0.48, 1.78), (ex, 2.01),
    (ex + 0.48, 1.78), (ex + 0.37, 1.12), (ex, 0.96),
    (ex - 0.37, 1.12)], ey + 0.42, 0.22, obsidian, enemy, 0.032)
cut_plate("hostile core socket", [(ex - 0.19, 1.51), (ex, 1.64),
    (ex + 0.19, 1.51), (ex + 0.16, 1.34),
    (ex, 1.26), (ex - 0.16, 1.34)],
    ey + 0.53, 0.035, steel_dark, enemy, 0.007)
cut_plate("hostile pulsing core", [(ex - 0.105, 1.50), (ex, 1.58),
    (ex + 0.105, 1.50), (ex + 0.08, 1.38),
    (ex, 1.33), (ex - 0.08, 1.38)],
    ey + 0.57, 0.022, magenta, enemy, 0.004)
faceted_orb("enemy horned skull", (ex, ey + 0.09, 2.21),
            (0.36, 0.38, 0.35), obsidian, enemy, 1)
cut_plate("enemy angular face", [(ex - 0.28, 2.30), (ex, 2.39),
    (ex + 0.28, 2.30), (ex + 0.18, 2.08), (ex, 1.98),
    (ex - 0.18, 2.08)], ey + 0.42, 0.08, steel_dark, enemy, 0.015)
for side in (-1, 1):
    cut_plate("enemy split magenta eye", [(ex + side * 0.045, 2.27),
        (ex + side * 0.23, 2.29), (ex + side * 0.20, 2.21),
        (ex + side * 0.06, 2.20)], ey + 0.48, 0.018,
        magenta, enemy, 0.004)
    x = ex + side * 0.26
    rod("enemy rear-jointed leg", (x, ey - 0.06, 1.08),
        (x + side * 0.09, ey - 0.29, 0.46), 0.14, obsidian, enemy)
    rod("enemy forward shin", (x + side * 0.09, ey - 0.29, 0.46),
        (x + side * 0.15, ey + 0.19, 0.12), 0.12, steel_dark, enemy)
    cut_plate("enemy blade shin", [(ex + side * 0.16, 0.83),
        (ex + side * 0.40, 0.81), (ex + side * 0.48, 0.43),
        (ex + side * 0.34, 0.28)], ey + 0.14, 0.18,
        obsidian, enemy, 0.013)
    cut_plate("enemy taloned foot", [(ex + side * 0.22, 0.28),
        (ex + side * 0.46, 0.25), (ex + side * 0.60, 0.04),
        (ex + side * 0.32, 0.08)], ey + 0.44, 0.29,
        obsidian, enemy, 0.014)
    cut_plate("enemy swept shoulder shell", [(ex + side * 0.31, 1.90),
        (ex + side * 0.74, 2.06), (ex + side * 0.92, 1.86),
        (ex + side * 0.73, 1.54), (ex + side * 0.43, 1.56)],
        ey + 0.17, 0.29, obsidian, enemy, 0.027)
    rod("enemy articulated arm", (ex + side * 0.71, ey, 1.67),
        (ex + side * 0.92, ey + 0.34, 0.94), 0.15,
        steel_dark, enemy)
    rod("enemy magenta arm conduit", (ex + side * 0.76, ey + 0.17, 1.60),
        (ex + side * 0.89, ey + 0.48, 1.07), 0.021,
        magenta, enemy, 8)
    cut_plate("enemy scythe forearm", [(ex + side * 0.82, 1.12),
        (ex + side * 1.10, 1.05), (ex + side * 1.18, 0.58),
        (ex + side * 0.99, 0.29), (ex + side * 0.89, 0.75)],
        ey + 0.55, 0.16, obsidian, enemy, 0.015)
    cone("rear-swept hostile horn", (ex + side * 0.29, ey - 0.12, 2.69),
         0.14, 0.0, 0.82, obsidian, enemy, 5, (0, side * 0.30, 0))
    cone("shoulder carapace spike", (ex + side * 0.73, ey - 0.11, 2.16),
         0.13, 0, 0.62, magenta, enemy, 5,
         (0, side * 0.40, 0))
    for scale in range(2):
        z = 1.43 - scale * 0.19
        cut_plate("hostile rib armor", [(ex + side * 0.15, z + 0.12),
            (ex + side * 0.43, z + 0.10), (ex + side * 0.32, z - 0.06),
            (ex + side * 0.13, z - 0.03)], ey + 0.47, 0.04,
            obsidian, enemy, 0.008)

# The concept character is long-legged rather than toy-proportioned. Bake the
# modeling transforms, lengthen the lower body, and shift the torso as one
# continuous rest-pose deformation before skin weights are assigned.
for part in list(hero.children):
    if part.type != "MESH":
        continue
    part.data.transform(part.matrix_world)
    part.matrix_world.identity()
    part_name = part.name.lower()
    if "shield" in part_name:
        # Keep every shield inset aligned while stretching the silhouette to
        # the slimmer, longer kite in the turnaround reference.
        for vertex in part.data.vertices:
            if "shield round" not in part_name:
                vertex.co.x = -1.22 + (vertex.co.x + 1.22) * 0.74
                vertex.co.z = 1.67 + (vertex.co.z - 1.67) * 1.27
            else:
                # Keep the boss circular while moving it with the face.
                vertex.co.z += (1.96 - 1.67) * 0.27
    if any(term in part_name for term in ("thigh", "knee", "greave",
                                            "sabaton", "boot", "heel")):
        center_x = sum(vertex.co.x for vertex in part.data.vertices) / len(part.data.vertices)
        for vertex in part.data.vertices:
            vertex.co.x = center_x + (vertex.co.x - center_x) * 0.92
    for vertex in part.data.vertices:
        z = vertex.co.z
        vertex.co.z = z * 1.19 if z <= 1.65 else z + 0.3135

# A real glTF skin: the same armature deforms the visor, plates, sword, shield,
# and cloth. Rigid armor uses one bone; cape vertices blend over two linked bones.
armature = bpy.data.armatures.new("Oath knight deform bones")
rig = bpy.data.objects.new("KNIGHT_RIG", armature)
bpy.context.collection.objects.link(rig)
rig.parent = hero
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")


def bone(name, head, tail, parent=None):
    result = armature.edit_bones.new(name)
    result.head = head
    result.tail = tail
    if parent:
        result.parent = armature.edit_bones[parent]
    return result


bone("Root", (0, 0, 0.05), (0, 0, 0.36))
bone("Pelvis", (0, 0, 1.70), (0, 0, 2.02), "Root")
bone("Spine", (0, 0, 2.02), (0, 0, 2.55), "Pelvis")
bone("Chest", (0, 0, 2.55), (0, 0, 2.89), "Spine")
bone("Neck", (0, 0, 2.89), (0, 0, 3.08), "Chest")
bone("Head", (0, 0, 3.08), (0, 0, 3.90), "Neck")
bone("Shield.L", (-1.22, 0.58, 1.70), (-1.22, 0.58, 2.05), "Chest")
for side, label in ((-1, "L"), (1, "R")):
    bone(f"UpperArm.{label}", (side * 0.60, 0, 2.80),
         (side * 0.81, 0, 2.22), "Chest")
    bone(f"Forearm.{label}", (side * 0.81, 0, 2.22),
         (side * 0.88, 0.05, 1.76), f"UpperArm.{label}")
    bone(f"Hand.{label}", (side * 0.88, 0.05, 1.76),
         (side * 0.91, 0.13, 1.52), f"Forearm.{label}")
    bone(f"Thigh.{label}", (side * 0.29, 0, 1.75),
         (side * 0.30, 0, 1.22), "Pelvis")
    bone(f"Shin.{label}", (side * 0.30, 0, 1.22),
         (side * 0.31, 0, 0.43), f"Thigh.{label}")
    bone(f"Foot.{label}", (side * 0.31, 0, 0.43),
         (side * 0.31, 0.37, 0.13), f"Shin.{label}")
    bone(f"CapeUpper.{label}", (side * 0.36, -0.36, 2.82),
         (side * 0.58, -0.58, 1.62), "Chest")
    bone(f"CapeLower.{label}", (side * 0.58, -0.58, 1.62),
         (side * 0.82, -0.87, 0.27), f"CapeUpper.{label}")
bpy.ops.object.mode_set(mode="OBJECT")


def part_center(part):
    points = [vertex.co for vertex in part.data.vertices]
    return Vector((sum(v.x for v in points) / len(points),
                   sum(v.y for v in points) / len(points),
                   sum(v.z for v in points) / len(points)))


def part_bone(part, center):
    name = part.name.lower()
    side = "L" if center.x < 0 else "R"
    if "shield" in name:
        return "Shield.L"
    if "sword" in name or "blade" in name:
        return "Hand.R"
    if "cape" in name or "mantle" in name:
        return "Chest" if "collar" in name else f"CapeUpper.{side}"
    if any(term in name for term in ("helmet", "helm", "crown", "brow",
                                     "eye lens", "nose guard", "chin chevron",
                                     "faceplate", "temple mechanism")):
        return "Head"
    if any(term in name for term in ("finger", "gauntlet", "grip")):
        return f"Hand.{side}"
    if any(term in name for term in ("forearm", "vambrace", "wrist")):
        return f"Forearm.{side}"
    if any(term in name for term in ("pauldron", "shoulder", "upper arm",
                                     "elbow")):
        return f"UpperArm.{side}"
    if any(term in name for term in ("boot", "sabaton", "heel", "toe")):
        return f"Foot.{side}"
    if any(term in name for term in ("greave", "shin", "knee")):
        return f"Shin.{side}"
    if "thigh" in name:
        return f"Thigh.{side}"
    if any(term in name for term in ("belt", "waist", "fauld")):
        return "Pelvis"
    if "abdominal" in name:
        return "Spine"
    return "Chest"


weighted_parts = {}
for part in list(hero.children):
    if part.type != "MESH":
        continue
    center = part_center(part)
    assigned = part_bone(part, center)
    weighted_parts[assigned] = weighted_parts.get(assigned, 0) + 1
    if assigned.startswith("CapeUpper."):
        side = assigned[-1]
        upper = part.vertex_groups.new(name=assigned)
        lower = part.vertex_groups.new(name=f"CapeLower.{side}")
        for vertex in part.data.vertices:
            fraction = max(0, min(1, (2.65 - vertex.co.z) / 2.5))
            lower_weight = fraction * 0.78
            upper.add([vertex.index], 1 - lower_weight, "REPLACE")
            if lower_weight > 0:
                lower.add([vertex.index], lower_weight, "REPLACE")
    else:
        group = part.vertex_groups.new(name=assigned)
        group.add(list(range(len(part.data.vertices))), 1.0, "REPLACE")
    modifier = part.modifiers.new("Knight skeletal deformation", "ARMATURE")
    modifier.object = rig
    part.parent = rig


def action(name, frames):
    result = bpy.data.actions.new(name)
    rig.animation_data_create().action = result
    for frame, state in frames:
        for pose_bone in rig.pose.bones:
            pose_bone.rotation_mode = "XYZ"
            pose_bone.rotation_euler = state.get(pose_bone.name, (0, 0, 0))
            pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame,
                                      group=pose_bone.name)
            if pose_bone.name == "Shield.L":
                pose_bone.location = state.get("Shield.Move", (0, 0, 0))
                pose_bone.keyframe_insert(data_path="location", frame=frame,
                                          group=pose_bone.name)
    return result


action("Idle", [
    (1, {"Chest": (0.0, 0, -0.012), "CapeUpper.L": (0.025, 0, 0.025),
         "CapeUpper.R": (-0.025, 0, -0.025),
         "CapeLower.L": (0.015, 0, 0.025), "CapeLower.R": (-0.015, 0, -0.025)}),
    (24, {"Chest": (0.018, 0, 0.012), "Head": (0, 0.02, 0),
          "CapeUpper.L": (-0.035, 0, -0.035),
          "CapeUpper.R": (0.035, 0, 0.035),
          "CapeLower.L": (-0.065, 0, -0.045),
          "CapeLower.R": (0.065, 0, 0.045)}),
    (48, {"Chest": (0.0, 0, -0.012), "CapeUpper.L": (0.025, 0, 0.025),
          "CapeUpper.R": (-0.025, 0, -0.025),
          "CapeLower.L": (0.015, 0, 0.025), "CapeLower.R": (-0.015, 0, -0.025)}),
])
action("Stride", [
    (1, {"Thigh.L": (0.35, 0, 0), "Thigh.R": (-0.35, 0, 0),
         "UpperArm.L": (-0.12, 0, 0), "UpperArm.R": (0.18, 0, 0)}),
    (7, {"Thigh.L": (0, 0, 0), "Thigh.R": (0, 0, 0),
         "Shin.L": (0.2, 0, 0), "Shin.R": (0.03, 0, 0)}),
    (13, {"Thigh.L": (-0.35, 0, 0), "Thigh.R": (0.35, 0, 0),
          "UpperArm.L": (0.12, 0, 0), "UpperArm.R": (-0.18, 0, 0)}),
    (19, {"Thigh.L": (0, 0, 0), "Thigh.R": (0, 0, 0),
          "Shin.L": (0.03, 0, 0), "Shin.R": (0.2, 0, 0)}),
    (25, {"Thigh.L": (0.35, 0, 0), "Thigh.R": (-0.35, 0, 0),
          "UpperArm.L": (-0.12, 0, 0), "UpperArm.R": (0.18, 0, 0)}),
])
action("Slash", [
    (1, {}),
    (10, {"Chest": (0, 0, -0.21), "UpperArm.R": (-0.80, 0.12, 0.48),
         "Forearm.R": (-0.28, 0, 0), "UpperArm.L": (-0.20, 0, 0)}),
    (16, {"Chest": (0, 0, -0.21), "UpperArm.R": (-0.80, 0.12, 0.48),
          "Forearm.R": (-0.28, 0, 0), "UpperArm.L": (-0.20, 0, 0)}),
    (23, {"Chest": (0, 0, 0.35), "UpperArm.R": (0.50, -0.10, -0.82),
          "Forearm.R": (0.42, 0, 0), "Thigh.R": (0.16, 0, 0)}),
    (29, {"Chest": (0, 0, 0.35), "UpperArm.R": (0.50, -0.10, -0.82),
          "Forearm.R": (0.42, 0, 0), "Thigh.R": (0.16, 0, 0)}),
    (42, {}),
])
action("Guard", [
    (1, {}),
    (10, {"UpperArm.L": (-0.52, 0.06, -0.12),
          "Forearm.L": (-0.20, 0, 0.18), "Chest": (0.06, 0, 0.03),
          "Shield.Move": (0.45, 0.38, 0.04),
          "Thigh.L": (0.10, 0, 0), "Thigh.R": (-0.08, 0, 0)}),
    (30, {"UpperArm.L": (-0.52, 0.06, -0.12),
          "Forearm.L": (-0.20, 0, 0.18), "Chest": (0.06, 0, 0.03),
          "Shield.Move": (0.45, 0.38, 0.04),
          "Thigh.L": (0.10, 0, 0), "Thigh.R": (-0.08, 0, 0)}),
    (42, {}),
])
rig.animation_data.action = bpy.data.actions["Idle"]
bpy.context.scene.frame_set(1)
print("Knight skin parts per bone:", weighted_parts)

# One mesh per material and movable group keeps browser draw calls bounded.
for parent in (arena, rig, enemy):
    by_material = {}
    for obj in list(parent.children):
        if obj.type == "MESH":
            by_material.setdefault(obj.data.materials[0].name, []).append(obj)
    for name, parts in by_material.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in parts:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.join()
        parts[0].name = f"{parent.name} | {name}"

OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", export_yup=True,
                          export_apply=True, export_animation_mode="ACTIONS")
print(f"Exported {OUT} ({OUT.stat().st_size} bytes)")
for image in bpy.data.images:
    if image.source == "FILE":
        image.pack()
shutil.rmtree(TEXTURE_DIR)
