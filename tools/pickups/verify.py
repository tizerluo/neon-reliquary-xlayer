"""独立校验已导出的掉落道具 GLB（只用标准库，不依赖 Blender）：节点名 / 原点 / 三角面 / 材质 / 发光 / 半透明 / 包围盒。

    python3 tools/pickups/verify.py [shard|vial|chest ...]        # 默认校验三个
"""

import colorsys
import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "visual-lab" / "assets" / "pickups"
IDS = ("shard", "vial", "chest")
BUDGET = {"shard": 80, "vial": 400, "chest": 1500}
MAT_LIMIT = {"shard": 2, "vial": 3, "chest": 4}
EMIT_HEX = {"shard": "#86d9e6", "vial": "#87ffb5"}          # 碎片 / 圣瓶：发光色必须是语义色原值
SRGB = lambda c: (c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)
FORBIDDEN = ("core", "eye", "heart", "slit")                  # glow 允许（碎片 / 液体 / 宝石与光环内圈确实要辉光），其余不允许


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


def hexof(rgb):
    return "#" + "".join(f"{round(max(0, min(1, SRGB(c))) * 255):02x}" for c in rgb[:3])


def hue_deg(hexcolor):
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


def mesh_stats(js, blob, mesh_idx):
    """返回 (三角面数, 局部包围盒 min, max, 有向体积, 绕序与法线相反的三角形数)。"""
    tris, lo, hi, volume, flipped = 0, [1e9] * 3, [-1e9] * 3, 0.0, 0
    for prim in js["meshes"][mesh_idx]["primitives"]:
        pos = accessor(js, blob, prim["attributes"]["POSITION"])
        nor = accessor(js, blob, prim["attributes"]["NORMAL"])
        idx = accessor(js, blob, prim["indices"])
        tris += len(idx) // 3
        for p in pos:
            lo = [min(a, b) for a, b in zip(lo, p)]
            hi = [max(a, b) for a, b in zip(hi, p)]
        for k in range(0, len(idx), 3):
            a, b, c = (pos[i] for i in idx[k:k + 3])
            e1 = [b[j] - a[j] for j in range(3)]
            e2 = [c[j] - a[j] for j in range(3)]
            n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
            vn = nor[idx[k]]
            if sum(n[j] * vn[j] for j in range(3)) < 0:
                flipped += 1
            volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
    return tris, lo, hi, volume, flipped


def check(pid):
    path = ASSETS / f"{pid}.glb"
    js, size, blob = load(path)
    problems = []
    nodes = js.get("nodes", [])
    for key in ("skins", "animations", "textures", "images", "cameras"):
        if js.get(key):
            problems.append(f"含 {key}")
    if any(("skin" in n) or ("matrix" in n) or ("rotation" in n) or ("scale" in n) for n in nodes):
        problems.append("节点带旋转 / 缩放 / 矩阵 / 蒙皮（应只有平移）")
    top = js["scenes"][js.get("scene", 0)]["nodes"]
    mesh_nodes = [(i, n) for i, n in enumerate(nodes) if "mesh" in n]

    # 节点：名字、原点（平移）、世界包围盒
    node_rows, tris_total = [], 0
    lo_w, hi_w = [1e9] * 3, [-1e9] * 3
    for i, n in mesh_nodes:
        t = n.get("translation", [0, 0, 0])
        tris, lo, hi, vol, flipped = mesh_stats(js, blob, n["mesh"])
        tris_total += tris
        wlo = [l + o for l, o in zip(lo, t)]
        whi = [h + o for h, o in zip(hi, t)]
        lo_w = [min(a, b) for a, b in zip(lo_w, wlo)]
        hi_w = [max(a, b) for a, b in zip(hi_w, whi)]
        node_rows.append(dict(name=n.get("name"), top=i in top, t=t, tris=tris, lo=lo, hi=hi, vol=vol, flipped=flipped))
        if flipped:
            problems.append(f"{n.get('name')}: {flipped} 个三角形绕序与法线相反")
        if vol <= 0:
            problems.append(f"{n.get('name')}: 有向体积 {vol:.5f} ≤ 0（法线朝内？）")
        if not (i in top):
            problems.append(f"{n.get('name')}: 不是顶层节点")
        for prim in js["meshes"][n["mesh"]]["primitives"]:
            extra = set(prim["attributes"]) - {"POSITION", "NORMAL"}
            if extra:
                problems.append(f"{n.get('name')}: 多余顶点属性 {sorted(extra)}")
    size_xyz = [h - l for l, h in zip(lo_w, hi_w)]
    center = [(l + h) / 2 for l, h in zip(lo_w, hi_w)]

    if tris_total > BUDGET[pid]:
        problems.append(f"三角面 {tris_total} 超预算 {BUDGET[pid]}")

    # 材质
    mats = []
    for m in js["materials"]:
        pbr = m.get("pbrMetallicRoughness", {})
        em = m.get("emissiveFactor", [0, 0, 0])
        strength = m.get("extensions", {}).get("KHR_materials_emissive_strength", {}).get("emissiveStrength", 1.0)
        glows = any(c > 0 for c in em)
        bc = pbr.get("baseColorFactor", [1, 1, 1, 1])
        mats.append(dict(name=m["name"], base=hexof(bc), alpha=bc[3] if len(bc) > 3 else 1.0, metal=pbr.get("metallicFactor", 1.0),
                         rough=pbr.get("roughnessFactor", 1.0), glows=glows, strength=strength if glows else 0.0,
                         emit=hexof(em) if glows else "-", mode=m.get("alphaMode", "OPAQUE"), double=m.get("doubleSided", False)))
        if glows and strength > 2.5:
            problems.append(f"材质 {m['name']} 自发光强度 {strength} > 2.5")
        if "baseColorTexture" in pbr or "emissiveTexture" in m:
            problems.append(f"材质 {m['name']} 用了贴图")
        low = m["name"].lower()
        if any(k in low for k in FORBIDDEN):
            problems.append(f"材质名 {m['name']} 含强辉光关键词")
        if "glow" in low and not glows:
            problems.append(f"材质名 {m['name']} 含 glow 却不发光")
        if pid in EMIT_HEX and glows and hexof(em) != EMIT_HEX[pid]:
            problems.append(f"材质 {m['name']} 发光色 {hexof(em)} 不是语义色 {EMIT_HEX[pid]}")
        if pid == "chest" and glows and not (35 <= hue_deg(hexof(em)) <= 50):
            problems.append(f"材质 {m['name']} 发光色 {hexof(em)} 色相 {hue_deg(hexof(em)):.0f}° 不在金色范围")
    if len(mats) > MAT_LIMIT[pid]:
        problems.append(f"材质 {len(mats)} 个 > {MAT_LIMIT[pid]}")

    # 各道具专项
    names = [r["name"] for r in node_rows]
    if pid == "shard":
        if any(m["double"] for m in mats):
            problems.append("碎片材质应为单面（doubleSided=false，上百个实例的填充率）")
        if len(node_rows) != 1:
            problems.append(f"碎片应为单个网格节点，实际 {len(node_rows)}")
        if not (0.55 <= size_xyz[1] <= 0.65):
            problems.append(f"碎片高 {size_xyz[1]:.3f} 不在 0.55–0.65 m")
        if max(abs(c) for c in center) > 0.03:
            problems.append(f"碎片包围盒中心 {center} 偏离原点")
    if pid == "vial":
        if len(node_rows) != 1:
            problems.append(f"圣瓶应为单个网格节点，实际 {len(node_rows)}")
        if not (0.65 <= size_xyz[1] <= 0.75):
            problems.append(f"圣瓶高 {size_xyz[1]:.3f} 不在 0.65–0.75 m")
        if max(abs(c) for c in center) > 0.03:
            problems.append(f"圣瓶包围盒中心 {center} 偏离原点")
        liquid = [m for m in mats if m["name"].lower().startswith("vial glow")]
        if not liquid or not (liquid[0]["mode"] == "BLEND" and liquid[0]["double"] and liquid[0]["alpha"] < 1 and liquid[0]["glows"]):
            problems.append("圣瓶液体材质不是 发光 + BLEND + 双面 + alpha<1")
        elif liquid[0]["strength"] > liquid[0]["alpha"] * 2.5 + 1e-6:
            problems.append("圣瓶液体发光强度未按透明度预乘")
    if pid == "chest":
        for need in ("CHEST_BODY", "CHEST_LID", "CHEST_HALO"):
            if need not in names:
                problems.append(f"缺少节点 {need}")
        rows = {r["name"]: r for r in node_rows}
        if {"CHEST_BODY", "CHEST_LID", "CHEST_HALO"} <= set(rows):
            body, lid, halo = rows["CHEST_BODY"], rows["CHEST_LID"], rows["CHEST_HALO"]
            if any(abs(v) > 1e-4 for v in body["t"]):
                problems.append(f"CHEST_BODY 原点应在底面中心，实际 {body['t']}")
            if abs(body["lo"][1]) > 0.005:
                problems.append(f"CHEST_BODY 底面应在 y=0，实际 {body['lo'][1]:.4f}")
            # 盖子：原点在后侧铰链轴上 → 盖子几何从铰链向 +Z（前）延伸，高度在铰链之上
            if not (-0.05 <= lid["lo"][2] and lid["hi"][2] >= 0.5 and lid["lo"][1] >= -0.03):
                problems.append(f"CHEST_LID 几何相对铰链原点不对：local z {lid['lo'][2]:.3f}..{lid['hi'][2]:.3f}，y {lid['lo'][1]:.3f}..")
            if abs(lid["t"][0]) > 1e-4 or lid["t"][1] < 0.3 or lid["t"][2] > -0.2:
                problems.append(f"CHEST_LID 铰链位置异常 {lid['t']}（应为 x=0、y≈0.40、z≈-0.28）")
            # 光环：原点 = 环心，环面水平
            hc = [(l + h) / 2 for l, h in zip(halo["lo"], halo["hi"])]
            if abs(hc[0]) > 0.01 or abs(hc[2]) > 0.01 or abs(hc[1]) > 0.03:
                problems.append(f"CHEST_HALO 包围盒中心 {hc} 不在节点原点")
            hs = [h - l for l, h in zip(halo["lo"], halo["hi"])]
            if not (hs[1] < 0.12 * min(hs[0], hs[2])):
                problems.append(f"CHEST_HALO 不是水平薄环：尺寸 {hs}")
            # 开盖方向：CHEST_LID 绕 X 轴旋转 -110°（three.js 的 rotation.x），盖子最前沿（local +Z 最大）必须翻到铰链之上
            front_z = max(v for v in (lid["hi"][2],))
            ang = -110 * 3.141592653589793 / 180
            y_open = 0.0 * math.cos(ang) - front_z * math.sin(ang)
            if y_open <= 0.3:
                problems.append(f"开盖 rotation.x=-110° 后盖子前沿相对铰链 y={y_open:.3f}，没有翻起来（符号不对？）")
            if halo["t"][1] <= lid["t"][1] + 0.4:
                problems.append("CHEST_HALO 没有悬在盖子上方")
        if not (0.95 <= size_xyz[0] <= 1.10):
            problems.append(f"圣物匣宽 {size_xyz[0]:.3f} 不在 0.95–1.10 m")
    return dict(id=pid, bytes=size, tris=tris_total, nodes=node_rows, lo=lo_w, hi=hi_w, size=size_xyz, center=center,
                mats=mats, problems=problems)


def main():
    ids = sys.argv[1:] or IDS
    bad = 0
    for pid in ids:
        r = check(pid)
        print(f"== {pid} 字节={r['bytes']} 三角面={r['tris']}/{BUDGET[pid]} 材质={len(r['mats'])}/{MAT_LIMIT[pid]}")
        print("   包围盒 glTF 世界 min", [round(v, 3) for v in r["lo"]], "max", [round(v, 3) for v in r["hi"]],
              "尺寸(X,Y,Z)", [round(v, 3) for v in r["size"]])
        for n in r["nodes"]:
            print(f"   节点 {n['name']}: 顶层={n['top']} 原点(平移)={[round(v, 3) for v in n['t']]} 三角面={n['tris']} "
                  f"局部包围盒 {[round(v, 3) for v in n['lo']]} .. {[round(v, 3) for v in n['hi']]}")
        for m in r["mats"]:
            glow = f"发光 {m['emit']} ×{round(m['strength'], 3)}" if m["glows"] else "不发光"
            alpha = f" {m['mode']}{' 双面' if m['double'] else ''} alpha={round(m['alpha'], 3)}" if m["mode"] != "OPAQUE" else ""
            print(f"   材质 {m['name']}: base={m['base']} metal={round(m['metal'], 2)} rough={round(m['rough'], 2)} {glow}{alpha}")
        for p in r["problems"]:
            print("   问题:", p)
        bad += bool(r["problems"])
    print("VERIFY", "FAIL" if bad else "OK")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
