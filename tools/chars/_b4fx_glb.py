"""Boss 4 特效轮：GLB 报告（系统 Python，只用标准库）。

    python3 tools/chars/_b4fx_glb.py [文件 ...]

默认依次报告旧版备份（art/review/archive/boss-4-prefx）与当前导出（visual-lab/assets/chars）的
展示版 / 游戏版：字节数、BLEND 材质、带网格节点数、图元数、三角面数、动画名、带“beam”名的节点与材质。
"""

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    b = Path(path).read_bytes()
    magic, ver, length = struct.unpack("<4sII", b[:12])
    assert magic == b"glTF", path
    off, js = 12, None
    while off < length:
        n, t = struct.unpack("<I4s", b[off:off + 8])
        if t == b"JSON":
            js = json.loads(b[off + 8:off + 8 + n])
        off += 8 + n
    return js, len(b)


def report(path):
    g, size = load(path)
    mats = g.get("materials", [])
    acc = g["accessors"]
    tris = prims = 0
    per_mat = {}
    for m in g.get("meshes", []):
        for p in m["primitives"]:
            prims += 1
            cnt = acc[p["indices"]]["count"] if "indices" in p else acc[p["attributes"]["POSITION"]]["count"]
            t = cnt // 3
            tris += t
            name = mats[p["material"]]["name"] if "material" in p else "?"
            per_mat[name] = per_mat.get(name, 0) + t
    nodes = g.get("nodes", [])
    mesh_nodes = [n for n in nodes if "mesh" in n]
    skinned = [n for n in mesh_nodes if "skin" in n]
    blend = [(m["name"], m.get("alphaMode"), m.get("doubleSided", False),
              m.get("emissiveFactor"), m.get("extensions", {}).get("KHR_materials_emissive_strength"))
             for m in mats if m.get("alphaMode") == "BLEND"]
    print(f"== {path}")
    print(f"   bytes {size}  tris {tris}  prims {prims}  mesh-nodes {len(mesh_nodes)} (skinned {len(skinned)})  "
          f"materials {len(mats)}  nodes {len(nodes)}  joints {sum(len(s['joints']) for s in g.get('skins', []))}")
    print(f"   BLEND materials: {len(blend)}")
    for b in blend:
        print("     ", b, "tris", per_mat.get(b[0]))
    print("   animations:", [(a["name"]) for a in g.get("animations", [])])
    print("   beam nodes:", [n["name"] for n in nodes if "beam" in n.get("name", "").lower()])
    print("   beam mats:", [(m["name"], m.get("alphaMode", "OPAQUE")) for m in mats if "beam" in m["name"].lower()])
    return tris, prims, len(mesh_nodes)


if __name__ == "__main__":
    files = sys.argv[1:] or [
        ROOT / "art/review/archive/boss-4-prefx/boss-4.glb", ROOT / "art/review/archive/boss-4-prefx/boss-4-game.glb",
        ROOT / "visual-lab/assets/chars/boss-4.glb", ROOT / "visual-lab/assets/chars/boss-4-game.glb"]
    for f in files:
        report(f)
