"""帷影刺客 Veil Stalker（零域军团 · 类型 3）：细长反关节腿、双臂骨白长刃、破帷尖兜帽的高速拦截杂兵。

Attack 为突进交叉斩。刚性挂骨实例化方案（13 节骨含燕尾 Tails，≤4 种材质）；构建逻辑在
chars/_legion_veil.py，与精英“帷影处刑者”共用。
"""

from chars import _legion, _legion_veil as body

TITLE = "Veil Stalker"
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
