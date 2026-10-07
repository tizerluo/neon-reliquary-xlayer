"""锁链苦修者 Chain Penitent（零域军团 · 类型 5）：缠链壮汉，背负带刺房形圣物箱，右拳拖链枷的厚血近战杂兵。

Attack 为链枷越顶砸地。刚性挂骨实例化方案（13 节骨，含链枷 Flail 骨；≤4 种材质）；构建逻辑在
chars/_legion_chain.py，与精英“锁链殉道者”共用。
"""

from chars import _legion, _legion_chain as body

TITLE = "Chain Penitent"
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
