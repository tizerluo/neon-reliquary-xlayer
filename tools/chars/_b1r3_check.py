"""Boss 1 第三轮私有检查：逐帧用 BVH 查翼与躯干 / 头颈、翼与翼之间的几何穿插（读 .blend，不改任何文件）。

    blender -b art/chars/boss-1/boss-1.blend --python tools/chars/_b1r3_check.py -- [步长] [动作,动作…]

把蒙皮网格按“顶点主权重骨”分成四类：
  body   躯干 / 头 / 颈 / 核心（非 Wing 骨）的实体网格（含鳞甲、腹板、头骨、冠、冰晶脊）
  wsolid 翼的实体件（翼骨套筒、轴毂、冰刺）
  mem    翼膜（半透明薄片）
  其余（光环 / 环绕冰棱等挂骨件）不参与。
每帧统计三角面相交对数：mem↔body、wsolid↔body、mem 左↔右、wsolid 左↔右；与静止帧（Idle:1）的基线相减后报告增量最大的帧。
基线里翼膜内侧本来就埋进躯干侧面，所以只看“增量”。
"""

import sys

import bpy
from mathutils.bvhtree import BVHTree

MEM_KEYS = ("membrane",)


def classify(obj):
    """(类别, 左右) 逐面分类：返回 {类别: [面三角列表]}，三角为 (v0, v1, v2) 顶点下标。"""
    me = obj.data
    names = {g.index: g.name for g in obj.vertex_groups}
    dom = []
    for v in me.vertices:
        if v.groups:
            g = max(v.groups, key=lambda x: x.weight)
            dom.append(names.get(g.group, ""))
        else:
            dom.append("")
    return dom


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    step = int(argv[0]) if argv else 2
    clips = argv[1].split(",") if len(argv) > 1 else ["Idle", "Move", "Attack", "Enrage"]
    arm = bpy.data.objects["BOSS_1_RIG"]
    scene = bpy.context.scene
    skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)]
    info = []
    for o in skinned:
        dom = classify(o)
        is_mem = any(k in o.name.lower() for k in MEM_KEYS)
        info.append((o, dom, is_mem))
    print("CHECK meshes", [(o.name.split("|")[-1].strip(), m) for o, _, m in info])

    def side_of(name):
        return "L" if name.endswith(".L") else ("R" if name.endswith(".R") else "")

    def groups(dg):
        out = {"body": ([], []), "wsolid_L": ([], []), "wsolid_R": ([], []), "mem_L": ([], []), "mem_R": ([], [])}
        tag.clear()
        for k in out:
            tag[k] = []
        for o, dom, is_mem in info:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            mw = o.matrix_world
            verts = [mw @ v.co for v in me.vertices]
            me.calc_loop_triangles()
            for t in me.loop_triangles:
                ds = [dom[i] for i in t.vertices]
                wing = [d.startswith("Wing") for d in ds]
                if is_mem:
                    sides = {side_of(d) for d in ds if d.startswith("Wing")}
                    key = "mem_L" if "L" in sides and "R" not in sides else ("mem_R" if "R" in sides and "L" not in sides else None)
                elif all(wing):
                    sides = {side_of(d) for d in ds}
                    key = "wsolid_L" if sides == {"L"} else ("wsolid_R" if sides == {"R"} else None)
                elif not any(wing):
                    key = "body"
                else:
                    key = None
                if key:
                    vs, fs = out[key]
                    base = len(vs)
                    vs.extend(verts[i] for i in t.vertices)
                    fs.append((base, base + 1, base + 2))
                    tag[key].append((ds[0], o.name.split("|")[-1].strip().replace("Pale Wyrm ", ""), verts[t.vertices[0]]))
            ev.to_mesh_clear()
        return {k: BVHTree.FromPolygons(v, f) if f else None for k, (v, f) in out.items()}

    tag = {}
    detail = {}

    def wing_min_z():
        """翼的所有网格点（顶点主权重为 Wing 骨）的最低高度。"""
        dg = bpy.context.evaluated_depsgraph_get()
        lo = 1e9
        for o, dom, is_mem in info:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            mw = o.matrix_world
            for i, v in enumerate(me.vertices):
                if dom[i].startswith("Wing"):
                    z = (mw @ v.co).z
                    if z < lo:
                        lo = z
            ev.to_mesh_clear()
        return lo

    def overlaps(a, b, ka=None, kb=None):
        if a is None or b is None:
            return 0
        pr = a.overlap(b)
        if ka:
            for ia, ib in pr:
                key = (tag[ka][ia][0], tag[ka][ia][1], tag[kb][ib][0], tag[kb][ib][1])
                detail[key] = detail.get(key, 0) + 1
        return len(pr)

    def measure():
        dg = bpy.context.evaluated_depsgraph_get()
        g = groups(dg)
        return {
            "mem-body": overlaps(g["mem_L"], g["body"], "mem_L", "body") + overlaps(g["mem_R"], g["body"], "mem_R", "body"),
            "wsolid-body": overlaps(g["wsolid_L"], g["body"], "wsolid_L", "body") +
            overlaps(g["wsolid_R"], g["body"], "wsolid_R", "body"),
            "mem L-R": overlaps(g["mem_L"], g["mem_R"]),
            "wsolid L-R": overlaps(g["wsolid_L"], g["wsolid_R"]) + overlaps(g["wsolid_L"], g["mem_R"]) +
            overlaps(g["wsolid_R"], g["mem_L"]),
        }

    arm.animation_data.action = bpy.data.actions["Idle"]
    scene.frame_set(1)
    detail.clear()
    base = measure()
    base_detail = dict(detail)
    print("CHECK baseline (Idle:1)", base)
    import os
    probe = [x for x in os.environ.get("B1_PROBE", "").split(",") if x]
    for clip in clips:
        act = bpy.data.actions[clip]
        arm.animation_data.action = act
        f0, f1 = map(int, act.frame_range)
        worst = {k: (0, 0) for k in base}
        zmin = (1e9, 0)
        for f in range(f0, f1 + 1, step):
            scene.frame_set(f)
            m = measure()
            wz = wing_min_z()
            if wz < zmin[0]:
                zmin = (wz, f)
            for k in base:
                d = m[k] - base[k]
                if d > worst[k][0]:
                    worst[k] = (d, f)
        print(f"CHECK {clip}: " + "  ".join(f"{k} +{v[0]}@{v[1]}" for k, v in worst.items()) +
              f"  wing min z {zmin[0]:.2f} m @{zmin[1]}")
        for spec in probe:
            c, f = spec.split(":")
            if c != clip:
                continue
            scene.frame_set(int(f))
            detail.clear()
            measure()
            top = sorted(((n - base_detail.get(k, 0), k) for k, n in detail.items()), reverse=True)[:8]
            print(f"CHECK probe {spec}: " + "; ".join(f"{k[0]}/{k[1]} x {k[2]}/{k[3]} +{n}" for n, k in top if n > 0))


main()
