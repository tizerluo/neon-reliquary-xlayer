"""场地 GLB 构建（游戏版）：地面 / 边界布景 / 场内道具 / 彩窗光柱。

    blender -b --python tools/build_arena.py -- <区域id> [--review] [--no-export] [--only game-north,overview ...]

区域 id：cathedral（琉璃大教堂，区域 0）。导出到 visual-lab/assets/arenas/<id>.glb；
贴图放在 art/arenas/<id>/textures/；--review 同时出 Cycles 审图（art/review/arenas/<id>/）。
审图拼印样与校验用系统 python3：
    python3 tools/arenas/sheet.py <区域id>        # 印样 art/review/sheets/check-arena-<id>.png
    python3 tools/arenas/verify.py <区域id>       # 只用标准库校验导出的 GLB

结构：tools/arenas/common.py（通用：网格构建器 / 材质 / 装配 / 导出 / 散布）、tools/arenas/textures.py（通用：可平铺噪声 / 沃罗诺伊 / PNG）、
tools/arenas/review.py（通用：审图渲染）、tools/arenas/<区域>.py + <区域>_tex.py（区域专属：配方）。
"""

import importlib
import os
import sys
import time
from pathlib import Path

import bpy

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from arenas import common as C  # noqa: E402

OUT = ROOT / "visual-lab" / "assets" / "arenas"


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = [a for a in args if a.startswith("--")]
    rest = [a for a in args if not a.startswith("--")]
    rid = rest[0] if rest else "cathedral"
    only = None
    if "--only" in args:
        only = args[args.index("--only") + 1].split(",")
        rest = [a for a in rest if a not in only]
    region = importlib.import_module(f"arenas.{rid}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    t0 = time.time()
    texdir = ROOT / "art" / "arenas" / rid / "textures"
    texdir.mkdir(parents=True, exist_ok=True)
    specs = region.make_specs(texdir)
    parts = region.build()
    print(f"BUILD parts {len(parts)} in {time.time() - t0:.1f}s")
    groups, objs, mats = C.assemble(parts, specs)

    # —— 预算（构建期） ——
    tris = {g: 0 for g in C.GROUPS}
    prims = 0
    for p in parts:
        t = C.count_tris(objs[p.name])
        tris[p.group] += t
        prims += len(objs[p.name].data.materials)
    total = sum(tris.values())
    print(f"ARENA {rid} TRIS {total} / {C.LIMITS['tris']}  " + "  ".join(f"{g} {t}" for g, t in tris.items())
          + f"  MESHES {len(parts)} PRIMS {prims} MATS {len(mats)}")
    if total > C.LIMITS["tris"] and not os.environ.get("ARENA_NOBUDGET"):
        raise SystemExit(f"三角面 {total} 超过预算 {C.LIMITS['tris']}")
    if prims > C.LIMITS["prims"] or len(mats) > C.LIMITS["mats"]:
        raise SystemExit(f"图元 {prims} / 材质 {len(mats)} 超过预算")

    path = OUT / f"{rid}.glb"
    if "--no-export" not in flags:
        C.export_glb(path, groups, objs)
        C.patch_glb(path, specs)
        before, after = C.slim_glb(path)
        print("EXPORTED", path, path.stat().st_size, f"(瘦身前 {before})")
        verify = importlib.import_module("arenas.verify")
        verify.main([rid])
    if "--review" in flags:
        from arenas import review
        review.render_all(region, objs, ROOT / "art" / "review" / "arenas" / rid, only=only)
    print("DONE", rid, f"{time.time() - t0:.1f}s")


main()
