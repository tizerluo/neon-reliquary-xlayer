"""裂隙猎犬 Rift Hound（零域军团 · 类型 1）：机械四足犬、分节脊背、发光颚、刃尾的高速冲锋杂兵。

刚性挂骨实例化方案（14 节骨，≤4 种材质）；Attack 为扑咬。构建逻辑在 chars/_legion_hound.py，与精英“裂隙头狼”共用。
"""

from chars import _legion, _legion_hound as body

TITLE = "Rift Hound"
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
