"""背面剔除体检（Blender 内运行，Workbench 渲染）：按材质拆出网格子集，分别开 / 关背面剔除，从上半球 16 个方向渲染并比对（游戏相机只会在上方）。
有差异 = 该材质有法线朝内的面（或开口壳体的内侧可见）。用来决定哪些材质可以安全地导出为单面（doubleSided=false）。

    blender -b --python tools/pickups/cullcheck.py -- [shard|vial|chest ...]
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from pickups import chest, geo, recipes  # noqa: E402

OUT = Path(bpy.app.tempdir)
BUILDERS = {"shard": recipes.build_shard, "vial": recipes.build_vial, "chest": chest.build_chest}
# 只取上半球的视角（游戏相机永远在上方；底面开口、看不到）
DIRS = [(0, 0, 1), (1, 1, 1), (-1, 1, 1), (1, -1, 1), (-1, -1, 1), (1, -1, 0.5), (-1, -1, 0.5), (0, -1, 0.5),
        (0, 1, 0.5), (1, 0, 0.5), (-1, 0, 0.5), (0, -1, 0.15), (1, 0, 0.15), (-1, 0, 0.15), (0, 1, 0.15), (0, -1, 0.78)]


def render(path, direction, ortho, target):
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("c")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho
    cam = bpy.data.objects.new("c", cam_data)
    scene.collection.objects.link(cam)
    cam.location = Vector(target) + Vector(direction).normalized() * 6
    up = "Y" if abs(Vector(direction).normalized().z) < 0.95 else "X"
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y" if up == "Y" else "X").to_euler()
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    img = bpy.data.images.load(str(path))
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3]
    bpy.data.images.remove(img)
    return arr


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ids = [a for a in args if not a.startswith("--")] or list(BUILDERS)
    for pid in ids:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = [geo.make_object(p.name, p.mesh, p.mats, p.loc) for p in BUILDERS[pid]()]
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = scene.render.resolution_y = 384
        scene.render.film_transparent = False
        sh = scene.display.shading
        sh.light, sh.color_type = "STUDIO", "MATERIAL"
        mats = sorted({m.name for o in objs for m in o.data.materials})
        pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        center, ortho = (lo + hi) / 2, max((hi - lo).length * 1.05, 0.5)
        # Workbench 只认全局的背面剔除开关，所以按材质把网格拆成子集，分别在 剔除开 / 关 下渲染比对
        for name in mats + ["(全部)"]:
            subs = []
            for o in objs:
                if name != "(全部)" and name not in [m.name for m in o.data.materials]:
                    continue
                c = o.copy()
                c.data = o.data.copy()
                scene.collection.objects.link(c)
                if name != "(全部)":
                    bm = bmesh.new()
                    bm.from_mesh(c.data)
                    keep = [i for i, m in enumerate(c.data.materials) if m.name == name]
                    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in keep], context="FACES")
                    bm.to_mesh(c.data)
                    bm.free()
                subs.append(c)
            for o in objs:
                o.hide_render = True
            res = {}
            for cull in (False, True):
                sh.show_backface_culling = cull
                res[cull] = [render(OUT / f"{pid}-{int(cull)}-{i}.png", d, ortho, center) for i, d in enumerate(DIRS)]
            fr = [float((np.abs(a_ - b_).max(axis=1) > 0.08).mean()) for a_, b_ in zip(res[False], res[True])]
            worst = max(fr)
            if os.environ.get("CULL_DUMP") and name == "(全部)":      # 把最差一个视角的 关 / 开 渲染存成 npy，便于排查
                k = fr.index(worst)
                np.save(f"{os.environ['CULL_DUMP']}/{pid}-off.npy", res[False][k])
                np.save(f"{os.environ['CULL_DUMP']}/{pid}-on.npy", res[True][k])
                print("CULLDUMP", pid, "view", k, DIRS[k])
            print(f"CULLCHECK {pid} {name}: 最大差异像素比例 {worst * 100:.3f}%  -> {'OK 可单面' if worst < 0.0005 else '有朝内 / 开口的面，保持双面'}")
            for c in subs:
                bpy.data.objects.remove(c)
            for o in objs:
                o.hide_render = False


main()
