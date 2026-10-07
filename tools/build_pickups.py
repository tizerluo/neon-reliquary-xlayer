"""掉落道具游戏版 GLB 构建：成长碎片 shard / 回复圣瓶 vial / 圣物匣 chest。

    blender -b --python tools/build_pickups.py -- [shard|vial|chest ...] [--review] [--game] [--no-export]

默认重建全部三个并导出到 visual-lab/assets/pickups/<id>.glb；--review 同时出 Cycles 审图（art/review/pickups/），
再用系统 python3 跑 tools/pickups/sheet.py 拼印样、tools/pickups/verify.py 校验导出的 GLB。
坐标：Blender Z 向上 → glTF Y 向上；道具正面朝 Blender -Y（= glTF +Z，游戏相机一侧）。
圣物匣是三个顶层命名节点 CHEST_BODY / CHEST_LID / CHEST_HALO，开盖 = CHEST_LID 绕 X 轴 -110°。
"""

import json
import os
import struct
import sys
from pathlib import Path

import bpy

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from pickups import chest, geo, recipes, review  # noqa: E402

OUT = ROOT / "visual-lab" / "assets" / "pickups"
BUILDERS = {"shard": recipes.build_shard, "vial": recipes.build_vial, "chest": chest.build_chest}


def build(pid, clear=True):
    """清空场景（clear=False 则保留已有对象）→ 建几何 → 返回 {节点名: 对象}（含三角面预算检查）。"""
    if clear:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = BUILDERS[pid]()
    objs = {}
    for p in parts:
        objs[p.name] = geo.make_object(p.name, p.mesh, p.mats, p.loc)
    tris = sum(geo.count_tris(o) for o in objs.values())
    mats = sorted({m.name for o in objs.values() for m in o.data.materials})
    print(f"PICKUP {pid} TRIS {tris} / {recipes.BUDGET[pid]} MATS {len(mats)} / {recipes.MAT_LIMIT[pid]} {mats}")
    for n, o in objs.items():
        print(f"   NODE {n} tris {geo.count_tris(o)} verts {len(o.data.vertices)} loc {tuple(round(v, 3) for v in o.location)}")
    if tris > recipes.BUDGET[pid] and not os.environ.get("PICKUP_NOBUDGET"):
        raise SystemExit(f"{pid}: 三角面 {tris} 超过预算 {recipes.BUDGET[pid]}")
    if len(mats) > recipes.MAT_LIMIT[pid]:
        raise SystemExit(f"{pid}: 材质 {len(mats)} 个超过 {recipes.MAT_LIMIT[pid]}")
    return objs


def export(pid, objs):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{pid}.glb"
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs.values():
        o.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(objs.values()))
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_animations=False, export_skins=False,
                              export_cameras=False, export_lights=False)
    mats = {m.name: m for o in objs.values() for m in o.data.materials}
    patch_materials(path, mats)
    print("EXPORTED", path, path.stat().st_size)


def patch_materials(path, materials):
    """Blender 导出会把发光色归一化；这里改回“语义色 + 原始强度”（辐射量不变），并给半透明材质补 glTF 的
    alphaMode=BLEND / doubleSided。圣瓶液体的强度在配方里已按透明度预乘。"""
    data = path.read_bytes()
    jlen = struct.unpack_from("<I", data, 12)[0]
    js = json.loads(data[20:20 + jlen])
    rest = data[20 + jlen:]
    for gm in js["materials"]:
        bm = materials.get(gm["name"])
        if bm is None:
            continue
        p = bm.node_tree.nodes["Principled BSDF"]
        alpha = p.inputs["Alpha"].default_value
        if alpha < 1.0:
            gm["alphaMode"] = "BLEND"
            gm["doubleSided"] = True
            bc = gm.setdefault("pbrMetallicRoughness", {}).setdefault("baseColorFactor", [1, 1, 1, 1])
            bc[3] = round(alpha, 4)
        strength = p.inputs["Emission Strength"].default_value
        if strength <= 0:
            continue
        gm["emissiveFactor"] = [round(c, 6) for c in p.inputs["Emission Color"].default_value[:3]]
        gm.setdefault("extensions", {})["KHR_materials_emissive_strength"] = {"emissiveStrength": round(strength, 4)}
        used = js.setdefault("extensionsUsed", [])
        if "KHR_materials_emissive_strength" not in used:
            used.append("KHR_materials_emissive_strength")
    blob = json.dumps(js, separators=(",", ":")).encode()
    blob += b" " * (-len(blob) % 4)
    out = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(blob) + len(rest)) + struct.pack("<I4s", len(blob), b"JSON") + blob + rest
    path.write_bytes(out)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = {a for a in args if a.startswith("--")}
    ids = [a for a in args if not a.startswith("--")] or list(BUILDERS)
    if "--game" in flags:       # 游戏机位总览：三个模型放进同一个场景
        bpy.ops.wm.read_factory_settings(use_empty=True)
        review.render_game({pid: build(pid, clear=False) for pid in BUILDERS})
        print("DONE game")
        return
    for pid in ids:
        objs = build(pid)
        if "--no-export" not in flags:
            export(pid, objs)
        if "--review" in flags:
            review.render(pid, objs)
    print("DONE", ids)


main()
