"""壁垒执事 Bulwark Deacon（零域军团 · 类型 2）：宽厚重甲构造体，左臂塔盾刻猩红圣印，右手翼缘钉锤。

重甲包围单位；Attack 为跨步盾击。刚性挂骨实例化方案（12 节骨，≤4 种材质）；构建逻辑在
chars/_legion_bulwark.py，与精英“壁垒院长”共用。
"""

from chars import _legion, _legion_bulwark as body

TITLE = "Bulwark Deacon"
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
