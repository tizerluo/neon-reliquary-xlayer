"""圣骸巨像 Reliquary Colossus（零域军团 · 类型 7）：3.2 m 石甲巨像，背负六角棺形圣骸、垂膝巨拳的最重型包围杂兵。

Attack 为双拳高举砸地。刚性挂骨实例化方案（12 节骨，≤4 种材质）；构建逻辑在 chars/_legion_colossus.py。
"""

from chars import _legion, _legion_colossus as body

TITLE = "Reliquary Colossus"
ACCENT = (1.0, 0.22, 0.28)
CLIPS = ("Move", "Attack")
GAME_TRIS = 2500
REVIEW_POSE = body.REVIEW_POSE


def build(ctx):
    return body.build(ctx, elite=False)


def skeleton(rig, st):
    _legion.skeleton(rig, st)


def animate(rig, st):
    body.animate(rig, st)
