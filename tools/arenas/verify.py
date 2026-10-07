"""独立校验已导出的场地 GLB（标准库；贴图色彩统计可选用 numpy，缺了就跳过）：
节点结构 / 三角面 / 图元 / 材质 / 贴图尺寸 / 包围盒 / 内部道具高度 / 边界外侧 / 南侧高度 / 发光 / 半透明 / 绕序。

    python3 tools/arenas/verify.py [区域id ...]        # 默认 cathedral；有问题时退出码为 1
"""

import colorsys
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "visual-lab" / "assets" / "arenas"

# 与 common.py 保持一致（这里不 import，保持独立）
PLAY_X, PLAY_Z = 44.0, 40.0
FLOOR_X, FLOOR_Z = 70.0, 66.0
CLEAN_R = 18.0
PROP_MAX_H = 0.6
SOUTH_MAX_H = 2.0
RAIL_MAX_H = 1.5
LIMITS = dict(tris=150000, prims=40, meshes=40, mats=12, tex=1024, bytes=12 * 1024 * 1024, emit=2.5, shaft_emit=1.5, shafts=6)
GROUPS_REQUIRED = ("ARENA_FLOOR", "ARENA_BOUNDS", "ARENA_PROPS")
GROUPS_OPTIONAL = ("ARENA_LIGHTS",)
FORBIDDEN = ("core", "glow", "eye", "heart", "slit")
TOL = 0.02
SRGB = lambda c: (c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)
MOODS = {"cathedral": "#70bdca", "archive": "#9ab7dd", "foundry": "#d8986d", "throne": "#b89ccd"}
# 光柱色相（度）按区域：大教堂是青 / 玫红；档案馆是冷白蓝（避开青：青是“成长碎片”的语义色）
SHAFT_HUES = {"cathedral": [(170, 205), (320, 350)], "archive": [(205, 232)], "foundry": [(25, 48)], "throne": [(245, 280)]}


def load(path):
    data = Path(path).read_bytes()
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


COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def accessor(js, blob, idx):
    acc = js["accessors"][idx]
    view = js["bufferViews"][acc["bufferView"]]
    code, size = COMP[acc["componentType"]]
    n = NCOMP[acc["type"]]
    stride = view.get("byteStride") or size * n
    base = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    scale = 1.0
    if acc.get("normalized") and acc["componentType"] in (5121, 5123):
        scale = 1.0 / (255.0 if acc["componentType"] == 5121 else 65535.0)
    if stride == size * n:
        flat = struct.unpack_from("<" + code * (n * acc["count"]), blob, base)
        if scale != 1.0:
            flat = [x * scale for x in flat]
        if n == 1:
            return list(flat)
        return [tuple(flat[i:i + n]) for i in range(0, len(flat), n)]
    out = []
    for i in range(acc["count"]):
        vals = struct.unpack_from("<" + code * n, blob, base + i * stride)
        if scale != 1.0:
            vals = tuple(x * scale for x in vals)
        out.append(vals if n > 1 else vals[0])
    return out


def node_world(js):
    """每个节点的世界平移（只处理平移 / 无旋转缩放；有旋转缩放会报问题）。返回 {node: (tx,ty,tz)}, 问题列表。"""
    nodes = js["nodes"]
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    out, problems = {}, []

    def world(i):
        if i in out:
            return out[i]
        n = nodes[i]
        if any(k in n for k in ("matrix", "rotation", "scale")):
            problems.append(f"节点 {n.get('name')} 带旋转 / 缩放 / 矩阵（应只有平移）")
        t = n.get("translation", [0, 0, 0])
        p = world(parent[i]) if i in parent else (0, 0, 0)
        out[i] = (p[0] + t[0], p[1] + t[1], p[2] + t[2])
        return out[i]

    for i in range(len(nodes)):
        world(i)
    return out, parent, problems


# ===== PNG / JPEG 头（尺寸）与 PNG 解码（统计）=====
def image_info(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h, depth, ctype = struct.unpack(">IIBB", data[16:26])
        return "png", w, h, ctype
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return "jpeg", w, h, 3
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return "?", 0, 0, 0


def decode_png(data):
    """8 位、非隔行 PNG → numpy 数组（h,w,c）；需要 numpy，失败返回 None。"""
    try:
        import numpy as np
    except ImportError:
        return None
    pos, idat, ihdr = 8, b"", None
    while pos < len(data):
        ln, tag = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + ln
    w, h, depth, ctype, _, _, interlace = ihdr
    if depth != 8 or interlace != 0 or ctype not in (0, 2, 4, 6):
        return None
    c = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(h, 1 + w * c)
    out = np.zeros((h, w * c), dtype=np.uint8)
    prev = np.zeros(w * c, dtype=np.int16)
    for y in range(h):
        f, row = raw[y, 0], raw[y, 1:].astype(np.int16)
        if f == 0:
            cur = row
        elif f == 2:
            cur = (row + prev) & 255
        else:
            cur = row.copy()
            for x in range(w * c):          # 1 / 3 / 4 型只能顺序还原
                a = cur[x - c] if x >= c else 0
                b = prev[x]
                cc = prev[x - c] if x >= c else 0
                if f == 1:
                    p = a
                elif f == 3:
                    p = (a + b) >> 1
                else:
                    pa, pb, pc = abs(b - cc), abs(a - cc), abs(a + b - 2 * cc)
                    p = a if (pa <= pb and pa <= pc) else (b if pb <= pc else cc)
                cur[x] = (cur[x] + p) & 255
        out[y] = cur
        prev = cur.astype(np.int16)
    return out.reshape(h, w, c)


def hexof(rgb):
    return "#" + "".join(f"{round(max(0, min(1, SRGB(c))) * 255):02x}" for c in rgb[:3])


def hsv_of(rgb_lin):
    r, g, b = (max(0, min(1, SRGB(c))) for c in rgb_lin[:3])
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v


def check(rid):
    path = ASSETS / f"{rid}.glb"
    js, size, blob = load(path)
    problems, notes = [], []
    nodes = js["nodes"]
    world, parent, wp = node_world(js)
    problems += wp
    for key in ("skins", "animations", "cameras"):
        if js.get(key):
            problems.append(f"含 {key}")
    if "KHR_lights_punctual" in js.get("extensionsUsed", []):
        problems.append("含灯光扩展")

    # —— 节点结构 ——
    top = js["scenes"][js.get("scene", 0)]["nodes"]
    top_names = [nodes[i].get("name") for i in top]
    for g in GROUPS_REQUIRED:
        if g not in top_names:
            problems.append(f"缺少顶层分组节点 {g}")
    for t in top_names:
        if t not in GROUPS_REQUIRED + GROUPS_OPTIONAL:
            problems.append(f"多余的顶层节点 {t}")

    def group_of(i):
        while i in parent:
            i = parent[i]
        return nodes[i].get("name")

    rows = []
    for i, n in enumerate(nodes):
        if "mesh" not in n:
            continue
        g = group_of(i)
        if g not in GROUPS_REQUIRED + GROUPS_OPTIONAL:
            problems.append(f"网格节点 {n.get('name')} 不在任何分组下")
        rows.append((i, n, g))

    # —— 网格统计 + 顶点（世界坐标）——
    groups = {}
    flipped = 0
    flipped_by = {}
    vc_mean = {}
    total_tris = 0
    prims = 0
    uv_span = {}
    for i, n, g in rows:
        t = world[i]
        for prim in js["meshes"][n["mesh"]]["primitives"]:
            prims += 1
            pos = accessor(js, blob, prim["attributes"]["POSITION"])
            nor = accessor(js, blob, prim["attributes"]["NORMAL"])
            idx = accessor(js, blob, prim["indices"])
            tris = len(idx) // 3
            total_tris += tris
            mat = js["materials"][prim["material"]]["name"] if "material" in prim else "(none)"
            gr = groups.setdefault(g, dict(tris=0, prims=0, meshes=set(), lo=[1e9] * 3, hi=[-1e9] * 3, bad=[], verts=[]))
            gr["tris"] += tris
            gr["prims"] += 1
            gr["meshes"].add(n.get("name"))
            for p in pos:
                for k in range(3):
                    v = p[k] + t[k]
                    gr["lo"][k] = min(gr["lo"][k], v)
                    gr["hi"][k] = max(gr["hi"][k], v)
            gr["verts"].append((n.get("name"), mat, pos, t))
            # 绕序与法线一致
            for k in range(0, len(idx), 3):
                a, b, c = (pos[j] for j in idx[k:k + 3])
                e1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
                e2 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
                nx, ny, nz = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
                vn = nor[idx[k]]
                ln = math.sqrt(nx * nx + ny * ny + nz * nz) * math.sqrt(vn[0] ** 2 + vn[1] ** 2 + vn[2] ** 2)
                # 严重反向才算翻面（断口处翘曲的四边形被拆成两个三角形时，夹角会略超过 90°，不算）
                if ln > 1e-12 and (nx * vn[0] + ny * vn[1] + nz * vn[2]) / ln < -0.35:
                    flipped += 1
                    flipped_by[mat] = flipped_by.get(mat, 0) + 1
            if "COLOR_0" in prim["attributes"]:
                cs = accessor(js, blob, prim["attributes"]["COLOR_0"])
                acc_ = vc_mean.setdefault(mat, [0.0, 0.0, 0.0, 0])
                for c_ in cs:
                    acc_[0] += c_[0]
                    acc_[1] += c_[1]
                    acc_[2] += c_[2]
                acc_[3] += len(cs)
            if "TEXCOORD_0" in prim["attributes"]:
                uv = accessor(js, blob, prim["attributes"]["TEXCOORD_0"])
                us, vs = [u[0] for u in uv], [u[1] for u in uv]
                uv_span[mat] = (min(us), max(us), min(vs), max(vs))
    if flipped:
        problems.append(f"{flipped} 个三角形绕序与顶点法线相反：{flipped_by}")
    prim_total = sum(g["prims"] for g in groups.values())
    mesh_total = len(rows)
    if total_tris > LIMITS["tris"]:
        problems.append(f"三角面 {total_tris} 超预算 {LIMITS['tris']}")
    if prim_total > LIMITS["prims"]:
        problems.append(f"图元 {prim_total} 超过 {LIMITS['prims']}")
    if mesh_total > LIMITS["meshes"]:
        problems.append(f"网格 {mesh_total} 超过 {LIMITS['meshes']}")
    if len(js["materials"]) > LIMITS["mats"]:
        problems.append(f"材质 {len(js['materials'])} 个超过 {LIMITS['mats']}")
    if size > LIMITS["bytes"]:
        problems.append(f"文件 {size} 字节超过 {LIMITS['bytes']}")

    # —— 分组几何规则 ——
    def verts_of(g):
        for name, mat, pos, t in groups.get(g, {}).get("verts", []):
            for p in pos:
                yield name, mat, p[0] + t[0], p[1] + t[1], p[2] + t[2]

    fl = groups.get("ARENA_FLOOR")
    if fl:
        lo, hi = fl["lo"], fl["hi"]
        if lo[0] > -FLOOR_X + 0.01 or hi[0] < FLOOR_X - 0.01 or lo[2] > -FLOOR_Z + 0.01 or hi[2] < FLOOR_Z - 0.01:
            problems.append(f"地面没有覆盖 x∈±{FLOOR_X}、z∈±{FLOOR_Z}：实际 x {lo[0]:.1f}..{hi[0]:.1f} z {lo[2]:.1f}..{hi[2]:.1f}")
        if lo[1] < -0.005 or hi[1] > 0.12:
            problems.append(f"地面高度应在 y∈[0, 0.12]：实际 {lo[1]:.3f}..{hi[1]:.3f}")
    bd = groups.get("ARENA_BOUNDS")
    south_max, rail_max, bad_in, tall = 0.0, 0.0, 0, 0.0
    if bd:
        for name, mat, x, y, z in verts_of("ARENA_BOUNDS"):
            if abs(x) < PLAY_X - TOL and abs(z) < PLAY_Z - TOL:
                bad_in += 1
            if z > PLAY_Z:
                south_max = max(south_max, y)
            near = (PLAY_X <= abs(x) < PLAY_X + 1.4 and abs(z) <= PLAY_Z) or (PLAY_Z <= abs(z) < PLAY_Z + 1.4 and abs(x) <= PLAY_X + 1.4)
            if near:
                rail_max = max(rail_max, y)
            tall = max(tall, y)
        if bad_in:
            problems.append(f"边界布景有 {bad_in} 个顶点落在可活动区域内（|x|<{PLAY_X} 且 |z|<{PLAY_Z}）")
        if south_max > SOUTH_MAX_H + TOL:
            problems.append(f"南侧（z>{PLAY_Z}）最高 {south_max:.2f} m > {SOUTH_MAX_H}")
        if rail_max > RAIL_MAX_H + TOL:
            problems.append(f"边界线 1.4 m 内的基座 / 栏杆最高 {rail_max:.2f} m > {RAIL_MAX_H}")
        if not (8.0 <= tall <= 20.5):
            problems.append(f"边界布景最高 {tall:.2f} m 不在 8–20 m")
        notes.append(f"边界布景：最高 {tall:.1f} m，边界线旁基座 / 栏杆最高 {rail_max:.2f} m，南侧最高 {south_max:.2f} m")
    pr = groups.get("ARENA_PROPS")
    prop_max, prop_r = 0.0, 1e9
    if pr:
        outside = 0
        for name, mat, x, y, z in verts_of("ARENA_PROPS"):
            prop_max = max(prop_max, y)
            prop_r = min(prop_r, math.hypot(x, z))
            if abs(x) > PLAY_X + TOL or abs(z) > PLAY_Z + TOL:
                outside += 1
        if outside:
            problems.append(f"场内道具有 {outside} 个顶点跑出可活动区域")
        if prop_max > PROP_MAX_H + TOL:
            problems.append(f"场内道具最高 {prop_max:.2f} m > {PROP_MAX_H}")
        if prop_r < CLEAN_R - 0.01:
            problems.append(f"场内道具进入中心 {CLEAN_R} m 半径（最近 {prop_r:.2f} m）")
        notes.append(f"场内道具：最高 {prop_max:.2f} m，离中心最近 {prop_r:.1f} m")
    lt = groups.get("ARENA_LIGHTS")
    if lt:
        if len(lt["meshes"]) > LIMITS["shafts"]:
            problems.append(f"光柱 {len(lt['meshes'])} 道 > {LIMITS['shafts']}")
        notes.append(f"光柱 {len(lt['meshes'])} 道：{sorted(lt['meshes'])}")

    # —— 材质 ——
    mats = []
    for m in js["materials"]:
        pbr = m.get("pbrMetallicRoughness", {})
        em = m.get("emissiveFactor", [0, 0, 0])
        strength = m.get("extensions", {}).get("KHR_materials_emissive_strength", {}).get("emissiveStrength", 1.0)
        glows = any(c > 0 for c in em) or "emissiveTexture" in m
        bc = pbr.get("baseColorFactor", [1, 1, 1, 1])
        alpha = bc[3] if len(bc) > 3 else 1.0
        mats.append(dict(name=m["name"], base=hexof(bc), alpha=alpha, glows=glows, strength=strength if glows else 0.0,
                         emit=hexof(em) if glows and "emissiveTexture" not in m else ("(贴图)" if glows else "-"),
                         mode=m.get("alphaMode", "OPAQUE"), double=m.get("doubleSided", False),
                         tex=[k for k in ("baseColorTexture", "normalTexture", "emissiveTexture", "metallicRoughnessTexture")
                              if k in m or k in pbr]))
        peak = max(em) * strength if glows else 0.0
        low = m["name"].lower()
        if glows and peak > LIMITS["emit"] + 1e-6:
            problems.append(f"材质 {m['name']} 自发光强度 {peak:.2f} > {LIMITS['emit']}")
        if any(k in low for k in FORBIDDEN):
            problems.append(f"材质名 {m['name']} 含强辉光关键词")
        if "shaft" in low:
            if not (m.get("alphaMode") == "BLEND" and m.get("doubleSided")):
                problems.append(f"光柱材质 {m['name']} 不是 BLEND + 双面")
            if not glows or strength > LIMITS["shaft_emit"] + 1e-6:
                problems.append(f"光柱材质 {m['name']} 强度 {strength} > {LIMITS['shaft_emit']} 或不发光")
            elif strength > alpha * 3.0 + 1e-6:
                problems.append(f"光柱材质 {m['name']} 发光强度没有按透明度预乘（强度 {strength}，alpha {alpha}）")
            h, s, v = hsv_of(em)
            hues = SHAFT_HUES.get(rid, SHAFT_HUES["cathedral"])
            if not any(lo <= h <= hi for lo, hi in hues):
                problems.append(f"光柱材质 {m['name']} 色相 {h:.0f}° 不在本区域允许的范围 {hues}")
        else:
            if m.get("alphaMode", "OPAQUE") != "OPAQUE":
                problems.append(f"非光柱材质 {m['name']} 用了半透明")
        # 颜色语义：不要大面积纯红
        if "baseColorTexture" not in pbr:
            h, s, v = hsv_of(bc)
            if (h >= 345 or h <= 12) and s > 0.55 and v > 0.35:
                problems.append(f"材质 {m['name']} 基础色 {hexof(bc)} 是饱和红（红色保留给敌方预警）")
        if glows and "emissiveTexture" not in m:
            h, s, v = hsv_of(em)
            if (h >= 345 or h <= 12) and s > 0.55:
                problems.append(f"材质 {m['name']} 发光色 {hexof(em)} 是饱和红")

    # —— 贴图 ——
    imgs = []
    for k, im in enumerate(js.get("images", [])):
        view = js["bufferViews"][im["bufferView"]]
        data = blob[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
        kind, w, h, ctype = image_info(data)
        imgs.append(dict(name=im.get("name"), kind=kind, w=w, h=h, bytes=len(data), data=data))
        if max(w, h) > LIMITS["tex"]:
            problems.append(f"贴图 {im.get('name')} {w}×{h} 超过 {LIMITS['tex']}")
    for s in js.get("samplers", []):
        if s.get("wrapS", 10497) != 10497 or s.get("wrapT", 10497) != 10497:
            problems.append("采样器不是 REPEAT（地面贴图要平铺）")
    floor_mat = next((m for m in js["materials"] if "floor" in m["name"].lower()), None)
    if floor_mat is not None:
        span = uv_span.get(floor_mat["name"])
        if span:
            su, sv = span[1] - span[0], span[3] - span[2]
            notes.append(f"地面 UV 跨度 {su:.1f} × {sv:.1f} 个贴图周期（平铺）")
            if su < 4 or sv < 4:
                problems.append(f"地面 UV 跨度只有 {su:.1f} × {sv:.1f}，没有平铺放大")
        if "normalTexture" not in floor_mat:
            problems.append("地面材质缺少法线贴图")
        if "baseColorTexture" not in floor_mat.get("pbrMetallicRoughness", {}):
            problems.append("地面材质缺少基础色贴图")
    # 贴图色彩统计（需要 numpy）：地面基础色平均亮度、红色占比；发光贴图覆盖率
    stats = {}
    for im in imgs:
        nm = (im["name"] or "").lower()
        if im["kind"] != "png" or not (("base" in nm) or ("emissive" in nm)):
            continue
        arr = decode_png(im["data"])
        if arr is None:
            continue
        rgb = arr[..., :3].astype("float32") / 255.0
        lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])
        if "emissive" in nm:
            stats[nm] = f"发光像素 {100 * float((lum > 0.12).mean()):.2f}%"
            if float((lum > 0.12).mean()) > 0.04:
                problems.append(f"发光贴图 {im['name']} 覆盖 {100 * float((lum > 0.12).mean()):.1f}% > 4%（引导线只该占很小面积）")
        else:
            mx, mn = rgb.max(axis=-1), rgb.min(axis=-1)
            sat = (mx - mn) / (mx + 1e-6)
            red = ((rgb[..., 0] == mx) & (rgb[..., 0] > rgb[..., 1] * 1.6) & (rgb[..., 0] > rgb[..., 2] * 1.4) & (sat > 0.55) & (mx > 0.35)).mean()
            stats[nm] = f"平均亮度 {float(lum.mean()):.3f}（sRGB 值），饱和红占比 {100 * float(red):.2f}%"
            if "floor" in nm:
                lin_ = ((rgb <= 0.04045) * rgb / 12.92 + (rgb > 0.04045) * ((rgb + 0.055) / 1.055) ** 2.4)
                lin_lum = float((0.2126 * lin_[..., 0] + 0.7152 * lin_[..., 1] + 0.0722 * lin_[..., 2]).mean())
                vc = vc_mean.get(floor_mat["name"] if floor_mat else "Arena Floor Mosaic")
                vcl = (0.2126 * vc[0] + 0.7152 * vc[1] + 0.0722 * vc[2]) / max(vc[3], 1) if vc else 1.0
                eff_lin = lin_lum * vcl
                eff = SRGB(eff_lin)
                stats[nm] += f"；乘顶点色后有效亮度（线性 {eff_lin:.3f} → sRGB {eff:.3f}）"
                if eff > 0.27:
                    problems.append(f"地面有效亮度 sRGB {eff:.2f} 偏亮（地面占画面 70%，要让角色和预警清楚可读）")
            if float(red) > 0.02:
                problems.append(f"贴图 {im['name']} 饱和红占 {100 * float(red):.1f}%")
    return dict(id=rid, bytes=size, tris=total_tris, prims=prim_total, meshes=mesh_total, groups=groups, mats=mats, imgs=imgs,
                problems=problems, notes=notes, stats=stats, flipped=flipped)


def run(ids):
    bad = 0
    for rid in ids:
        r = check(rid)
        print(f"== {rid}  字节 {r['bytes']}（{r['bytes'] / 1048576:.2f} MB）  三角面 {r['tris']}/{LIMITS['tris']}  "
              f"网格 {r['meshes']}  图元 {r['prims']}/{LIMITS['prims']}  材质 {len(r['mats'])}/{LIMITS['mats']}")
        for gname, g in r["groups"].items():
            print(f"   {gname}: 三角面 {g['tris']}  网格 {len(g['meshes'])}  图元 {g['prims']}  "
                  f"包围盒 x {g['lo'][0]:.1f}..{g['hi'][0]:.1f}  y {g['lo'][1]:.2f}..{g['hi'][1]:.2f}  z {g['lo'][2]:.1f}..{g['hi'][2]:.1f}")
        for m in r["mats"]:
            glow = f"发光 {m['emit']} ×{m['strength']:.3g}" if m["glows"] else "不发光"
            alpha = f" {m['mode']}{' 双面' if m['double'] else ''} alpha={m['alpha']:.2f}" if m["mode"] != "OPAQUE" else ("  双面" if m["double"] else "")
            print(f"   材质 {m['name']}: base={m['base']} {glow}{alpha} 贴图={','.join(t.replace('Texture', '') for t in m['tex']) or '-'}")
        for im in r["imgs"]:
            print(f"   贴图 {im['name']}: {im['kind']} {im['w']}×{im['h']} {im['bytes'] / 1024:.0f} KB")
        for k, v in r["stats"].items():
            print(f"   贴图统计 {k}: {v}")
        for n in r["notes"]:
            print("   " + n)
        for p in r["problems"]:
            print("   问题:", p)
        bad += bool(r["problems"])
    print("VERIFY", "FAIL" if bad else "OK")
    return not bad


def main(ids=None):
    ok = run(ids or sys.argv[1:] or ["cathedral"])
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
