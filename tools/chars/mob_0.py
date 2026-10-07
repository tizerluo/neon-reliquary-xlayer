"""空壳仆从 Husk Thrall（零域军团 · 类型 0）：佝偻人形、独眼骨白面具、右前臂锈刃的基础近战杂兵。

刚性挂骨实例化方案（12 节骨，≤4 种材质）；构建逻辑在 chars/_legion_husk.py，与精英“仆从百夫长”共用。
"""

from chars import _legion, _legion_husk as body

TITLE = "Husk Thrall"
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
