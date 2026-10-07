"""Boss 7（灰烬炽天使）第五轮：合并网格降绘制调用。

第四轮的 207 个网格节点 / 214 个图元，几乎全部来自 kit 的“挂骨件”：翅膀羽片 / 翼骨、火舌（Flare / WFlare / Dart 骨）、
剑、余烬碎片按（骨, 材质）逐组合并后各占一个节点。第五轮把它们改成 rigid 蒙皮（权重 1.0 绑在原来挂的那根骨上）：
kit.rig._merge_skinned 随后把所有蒙皮件按材质合并，整个角色只剩“一材质一网格”（约 25 个）+ 光环网格。

骨骼缩放通道（Flare 火舌燃起、Dart 羽刃缩放隐去）对蒙皮同样生效：顶点绕骨头部缩放，与第四轮挂骨件
（骨父级矩阵 × 逆静止矩阵）等价。BOSS_7_HALO 仍用 keep=True 保持独立节点（网页端按名字驱动自转）。
"""

from kit.core import rigid


def skin_attach(ctx):
    """把 ctx.attach 换成“刚性蒙皮”：keep=True（光环）仍走原挂骨路径，其余登记为 rigid 蒙皮部件。"""
    original = ctx.attach

    def attach(obj, bone, keep=False):
        if keep:
            return original(obj, bone, keep=True)
        return ctx.part(obj, rigid(bone))
    ctx.attach = attach
