"""独立校验已导出的 GLB（只用标准库，不依赖 Blender）：节点 / 骨骼 / 动画 / 材质 / 贴图 / 面数 / 包围盒。

    python3 tools/blades/verify.py [id ...]        # 默认校验六把
"""

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "visual-lab" / "assets" / "blades"
IDS = ("aurelian", "mordred", "volt", "nyx", "seraph", "isolde")
THEME = {"aurelian": "#7cece1", "mordred": "#ffac64", "volt": "#86b9ff", "nyx": "#c39bff", "seraph": "#ff8ea8", "isolde": "#9beefb"}
BUDGET = {"nyx": 200}
SRGB = lambda c: (c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)


def load(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF" and length == len(data), "不是合法 GLB"
    off, js, blob = 12, None, b""
    while off < len(data):
        clen, ctype = struct.unpack_from("<I4s", data, off)
        if ctype == b"JSON":
            js = json.loads(data[off + 8: off + 8 + clen])
        elif ctype == b"BIN\x00":
            blob = data[off + 8: off + 8 + clen]
        off += 8 + clen
    return js, len(data), blob


def accessor(js, blob, idx):
    """读出访问器数据，返回元组列表（标量返回数）。"""
    acc = js["accessors"][idx]
    view = js["bufferViews"][acc["bufferView"]]
    code, size = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4)}[acc["componentType"]]
    n = {"SCALAR": 1, "VEC3": 3}[acc["type"]]
    stride = view.get("byteStride") or size * n
    base = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    out = []
    for i in range(acc["count"]):
        vals = struct.unpack_from("<" + code * n, blob, base + i * stride)
        out.append(vals if n > 1 else vals[0])
    return out


def mesh_sanity(js, blob):
    """三角形绕序与顶点法线一致、整体有向体积为正（法线朝外）。返回 (反向三角形数, 有向体积 m³)。"""
    flipped, volume = 0, 0.0
    for prim in js["meshes"][0]["primitives"]:
        pos = accessor(js, blob, prim["attributes"]["POSITION"])
        nor = accessor(js, blob, prim["attributes"]["NORMAL"])
        idx = accessor(js, blob, prim["indices"])
        for k in range(0, len(idx), 3):
            a, b, c = (pos[i] for i in idx[k:k + 3])
            e1 = [b[j] - a[j] for j in range(3)]
            e2 = [c[j] - a[j] for j in range(3)]
            n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
            vn = nor[idx[k]]
            if sum(n[j] * vn[j] for j in range(3)) < 0:
                flipped += 1
            volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
    return flipped, volume


def hexof(rgb):
    return "#" + "".join(f"{round(max(0, min(1, SRGB(c))) * 255):02x}" for c in rgb[:3])


def check(cid):
    path = ASSETS / f"{cid}-blade.glb"
    js, size, blob = load(path)
    problems = []
    meshes, nodes = js.get("meshes", []), js.get("nodes", [])
    mesh_nodes = [n for n in nodes if "mesh" in n]
    if len(meshes) != 1 or len(mesh_nodes) != 1:
        problems.append(f"网格 {len(meshes)} 个 / 网格节点 {len(mesh_nodes)} 个（应各为 1）")
    for key in ("skins", "animations", "textures", "images", "cameras"):
        if js.get(key):
            problems.append(f"含 {key}")
    if any(("skin" in n) or ("matrix" in n) or ("rotation" in n) or ("scale" in n) or ("translation" in n) for n in nodes):
        problems.append("节点带变换 / 蒙皮（应为单位变换）")
    tris, lo, hi = 0, [1e9] * 3, [-1e9] * 3
    for prim in meshes[0]["primitives"]:
        acc = js["accessors"][prim["attributes"]["POSITION"]]
        lo = [min(a, b) for a, b in zip(lo, acc["min"])]
        hi = [max(a, b) for a, b in zip(hi, acc["max"])]
        tris += js["accessors"][prim["indices"]]["count"] // 3 if "indices" in prim else acc["count"] // 3
        extra = set(prim["attributes"]) - {"POSITION", "NORMAL"}
        if extra:
            problems.append(f"多余顶点属性 {sorted(extra)}")
    mats = []
    for m in js["materials"]:
        pbr = m.get("pbrMetallicRoughness", {})
        em = m.get("emissiveFactor", [0, 0, 0])
        strength = m.get("extensions", {}).get("KHR_materials_emissive_strength", {}).get("emissiveStrength", 1.0)
        glows = any(c > 0 for c in em)
        mats.append((m["name"], hexof(pbr.get("baseColorFactor", [1, 1, 1])), pbr.get("metallicFactor"),
                     pbr.get("roughnessFactor"), glows, strength if glows else 0, hexof(em) if glows else "-"))
        if glows and hexof(em) != THEME[cid]:
            problems.append(f"材质 {m['name']} 发光色 {hexof(em)} 不是主题色 {THEME[cid]}")
        if glows and strength > 2.5:
            problems.append(f"材质 {m['name']} 自发光强度 {strength} > 2.5")
        if "baseColorTexture" in pbr or "emissiveTexture" in m:
            problems.append(f"材质 {m['name']} 用了贴图")
    if len(mats) > 3:
        problems.append(f"材质 {len(mats)} 个 > 3")
    if tris > BUDGET.get(cid, 300):
        problems.append(f"三角面 {tris} 超预算")
    flipped, volume = mesh_sanity(js, blob)
    if flipped:
        problems.append(f"{flipped} 个三角形绕序与法线相反")
    if volume <= 0:
        problems.append(f"有向体积 {volume:.5f} ≤ 0（法线朝内）")
    size_xyz = [h - l for l, h in zip(lo, hi)]
    if not (0.80 <= hi[0] <= 0.90 and -0.60 <= lo[0] <= -0.50):
        problems.append(f"X 范围 {lo[0]:.3f}..{hi[0]:.3f} 偏离 剑尖≈+0.85 / 剑首≈-0.55")
    if not (size_xyz[1] < size_xyz[2] or True):  # glTF Y 为厚度方向
        pass
    if size_xyz[1] > 0.12:
        problems.append(f"厚度方向 Y 跨度 {size_xyz[1]:.3f} 偏大")
    return dict(id=cid, node=(mesh_nodes[0].get("name") if mesh_nodes else None), tris=tris, bytes=size, volume=volume,
                lo=lo, hi=hi, size=size_xyz, mats=mats, problems=problems)


def main():
    ids = sys.argv[1:] or IDS
    bad = 0
    for cid in ids:
        r = check(cid)
        print(f"== {cid} 节点={r['node']} 三角面={r['tris']} 字节={r['bytes']} 有向体积={r['volume']:.5f} m³")
        print("   包围盒 glTF 坐标 min", [round(v, 3) for v in r["lo"]], "max", [round(v, 3) for v in r["hi"]],
              "尺寸(X,Y,Z)", [round(v, 3) for v in r["size"]])
        for name, base, metal, rough, glows, strength, emit in r["mats"]:
            print(f"   材质 {name}: base={base} metal={1.0 if metal is None else round(metal, 2)} rough={round(rough, 2)} "
                  f"{'发光 ' + emit + ' ×' + str(round(strength, 2)) if glows else '不发光'}")
        for p in r["problems"]:
            print("   问题:", p)
        bad += bool(r["problems"])
    print("VERIFY", "FAIL" if bad else "OK")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
