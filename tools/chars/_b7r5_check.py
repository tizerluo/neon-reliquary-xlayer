"""Boss 7 第五轮：合并网格后的动画回归检查（Blender 里导入两份游戏版 GLB，逐动作逐帧比较每种材质的姿态下包围盒）。

    blender -b --python tools/chars/_b7r5_check.py -- <旧 GLB 绝对路径> <新 GLB 绝对路径>

挂骨件改刚性蒙皮后，翅膀 / 火舌 / 羽刃 / 剑 / 余烬应与第四轮逐帧一致（减面的细微差异除外）。输出每种材质在各帧的最大包围盒偏差（米）。
"""

import sys
from pathlib import Path

import bpy
import numpy as np

FRAMES = [("Idle", 1), ("Idle", 37), ("Move", 9), ("Move", 25), ("Attack", 10), ("Attack", 15), ("Attack", 18),
          ("Attack", 22), ("Attack", 30), ("Enrage", 12), ("Enrage", 20), ("Enrage", 32), ("Enrage", 40)]


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o.type == "MESH"], [o for o in bpy.data.objects if o.type == "ARMATURE"][0]


def pose(arm, name, frame):
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = bpy.data.actions[name]
    slots = getattr(ad, "action_suitable_slots", None)
    if slots:
        ad.action_slot = slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def boxes(meshes):
    """材质名 -> (min, max)（姿态下世界坐标；BOSS_7_HALO 节点单独记）。"""
    dg = bpy.context.evaluated_depsgraph_get()
    acc = {}
    for o in meshes:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        n = len(me.vertices)
        co = np.empty(n * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(n, 3)
        co = co @ np.array(ev.matrix_world, np.float32)[:3, :3].T + np.array(ev.matrix_world, np.float32)[:3, 3]
        pm = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get("material_index", pm)
        for mi, slot in enumerate(o.material_slots):
            faces = np.nonzero(pm == mi)[0]
            if not len(faces):
                continue
            vs = set()
            for f in faces:
                vs.update(me.polygons[f].vertices)
            pts = co[sorted(vs)]
            key = "HALO:" + slot.material.name if o.name.startswith("BOSS_7_HALO") else slot.material.name
            lo, hi = pts.min(axis=0), pts.max(axis=0)
            if key in acc:
                lo, hi = np.minimum(acc[key][0], lo), np.maximum(acc[key][1], hi)
            acc[key] = (lo, hi)
        ev.to_mesh_clear()
    return acc


def main():
    old, new = sys.argv[sys.argv.index("--") + 1:][:2]
    res = {}
    for tag, path in (("old", old), ("new", new)):
        meshes, arm = load(path)
        for name, frame in FRAMES:
            pose(arm, name, frame)
            res[(tag, name, frame)] = boxes(meshes)
    worst = {}
    for name, frame in FRAMES:
        a, b = res[("old", name, frame)], res[("new", name, frame)]
        for mat in sorted(set(a) | set(b)):
            if mat not in a or mat not in b:
                worst.setdefault(mat, []).append((99.0, f"{name}:{frame} missing in {'new' if mat in a else 'old'}"))
                continue
            d = max(np.abs(a[mat][0] - b[mat][0]).max(), np.abs(a[mat][1] - b[mat][1]).max())
            worst.setdefault(mat, []).append((float(d), f"{name}:{frame}"))
    print("CHECK 每材质最大包围盒偏差（米）/ 出现帧")
    for mat, lst in sorted(worst.items()):
        d, where = max(lst)
        print(f"CHECK {d:7.3f}  {where:16s} {mat}")


if __name__ == "__main__":
    main()
