"""按角色配方构建 GLB：几何 → 骨骼 → 蒙皮 → 动作 → 展示版 + 游戏版导出（可选审图）。

    blender -b --python tools/build_char.py -- <角色id> [--geo] [--review] [--no-export]

--geo       只建几何并渲染审图（不绑骨、不导出），用于快速迭代造型
--review    绑骨与动作完成后，在导出前渲染待机首帧审图
配方模块位于 tools/chars/<id>.py，需提供：TITLE、ACCENT、CLIPS、build(ctx)、skeleton(rig, st)、
animate(rig, st)；可选 GAME_TRIS、LOD_KEEP、REVIEW_POSE（审图用的动作名与帧）。
产物：visual-lab/assets/chars/<id>.glb、<id>-game.glb，art/chars/<id>/<id>.blend，art/review/chars/<id>/*.png
"""

import importlib
import sys
import time
from pathlib import Path

import bpy

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from kit.core import ROOT, Ctx  # noqa: E402
from kit.rig import Rig  # noqa: E402
from kit import review  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not args:
    raise SystemExit("usage: blender -b --python tools/build_char.py -- <id> [--geo] [--review]")
cid = args[0]
started = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 24
recipe = importlib.import_module(f"chars.{cid.replace('-', '_')}")
ctx = Ctx(cid, recipe.TITLE)
st = recipe.build(ctx)
print(f"GEOMETRY {cid}: {len(ctx.parts)} skinned parts, {len(ctx.attached)} attached, {time.time() - started:.1f}s")

if "--geo" in args:
    root = bpy.data.objects.new(ctx.ID, None)
    bpy.context.scene.collection.objects.link(root)
    for obj, _ in ctx.parts:
        obj.parent = root
    for obj, *_ in ctx.attached:
        obj.parent = root
    for obj in ctx.hidden:
        obj.parent = root
    review.render(cid, root, recipe.ACCENT, tag="-geo")
    raise SystemExit(0)

rig = Rig(ctx)
recipe.skeleton(rig, st)
rig.done()
rig.bind()
recipe.animate(rig, st)
rig.motion_check(list(recipe.CLIPS))
clip, frame = getattr(recipe, "REVIEW_POSE", (recipe.CLIPS[0], 1))
rig.obj.animation_data.action = bpy.data.actions[clip]
bpy.context.scene.frame_set(frame)
for obj in ctx.hidden:
    obj.parent = rig.root
print("MESHES", {o.name: len(o.data.polygons) for o in rig.meshes}, "BONES", len(rig.data.bones))
rig.save_blend(ROOT / "art" / "chars" / cid / f"{cid}.blend")
if "--review" in args:
    review.render(cid, rig.root, recipe.ACCENT)
    # CHAR_POSES="Move:5,Cast:14" 额外渲染指定动作帧（视角取 CHAR_POSE_VIEWS，默认正面 + 四分之三）
    import os
    for spec in filter(None, os.environ.get("CHAR_POSES", "").split(",")):
        name, f = spec.split(":")
        rig.obj.animation_data.action = bpy.data.actions[name]
        bpy.context.scene.frame_set(int(f))
        review.render(cid, rig.root, recipe.ACCENT, views=os.environ.get("CHAR_POSE_VIEWS", "front,three-quarter").split(","),
                      tag=f"-{name.lower()}{f}")
    rig.obj.animation_data.action = bpy.data.actions[clip]
    bpy.context.scene.frame_set(frame)
if "--no-export" not in args:
    out = ROOT / "visual-lab" / "assets" / "chars"
    rig.export(out / f"{cid}.glb", out / f"{cid}-game.glb", target=getattr(recipe, "GAME_TRIS", 60000),
               keep=getattr(recipe, "LOD_KEEP", ("inlay", "glow", "hem", "trim", "core")))
print(f"DONE {cid} in {time.time() - started:.1f}s")
