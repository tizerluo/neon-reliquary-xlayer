"""六套圣物飞剑 · 游戏版低面数 GLB 构建。

    blender -b --python tools/build_blades.py -- [id ...] [--review] [--no-export]

默认重建全部六把并导出到 visual-lab/assets/blades/<id>-blade.glb；--review 同时出 Cycles 审图
（art/review/blades/）。审图拼印样：python3 tools/blades/sheet.py。
坐标：Blender Z 向上 → glTF Y 向上，剑尖 +X 保持不变，宽面朝 +Y。
"""

import json
import struct
import sys
from pathlib import Path

import bpy

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from blades import geo, recipes, review  # noqa: E402

OUT = ROOT / "visual-lab" / "assets" / "blades"


def build(cid):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = geo.Mesh()
    materials = recipes.RECIPES[cid](mesh)
    obj = geo.make_object(f"{cid.upper()}_BLADE", mesh, materials)
    tris = geo.count_tris(obj)
    budget = recipes.BUDGET[cid]
    print(f"BLADE {cid} TRIS {tris} / {budget} VERTS {len(obj.data.vertices)} MATS {[m.name for m in obj.data.materials]}")
    if tris > budget:
        raise SystemExit(f"{cid}: 三角面 {tris} 超过预算 {budget}")
    return obj


def export(cid, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{cid}-blade.glb"
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_animations=False, export_skins=False,
                              export_cameras=False, export_lights=False)
    patch_emissive(path, list(obj.data.materials))
    print("EXPORTED", path, path.stat().st_size)


def patch_emissive(path, materials):
    """Blender 导出时会把发光色归一化（色相不变、强度折算）；这里改回“主题色 + 原始强度”，
    让 glTF 里的 emissiveFactor 就是 NRCOLORS 的线性值，便于核对颜色语义（辐射量不变）。"""
    data = path.read_bytes()
    jlen = struct.unpack_from("<I", data, 12)[0]
    js = json.loads(data[20:20 + jlen])
    rest = data[20 + jlen:]
    for gm in js["materials"]:
        bm = next((m for m in materials if m.name == gm["name"]), None)
        p = bm.node_tree.nodes["Principled BSDF"] if bm else None
        strength = p.inputs["Emission Strength"].default_value if p else 0
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
    ids = [a for a in args if not a.startswith("--")] or list(recipes.RECIPES)
    for cid in ids:
        obj = build(cid)
        if "--no-export" not in flags:
            export(cid, obj)
        if "--review" in flags:
            review.render(cid, obj, recipes.COLORS[cid], recipes.DETAIL[cid])
    print("DONE", ids)


main()
