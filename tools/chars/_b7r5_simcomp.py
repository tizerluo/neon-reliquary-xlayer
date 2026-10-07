"""Boss 7 第五轮：游戏条件模拟的合成一侧（系统 Python，需要 numpy + Pillow；不在 Blender 里跑）。

    python3 tools/chars/_b7r5_simcomp.py <目录> <标签>

读 _b7r5_shots.py sim 输出的 <标签>_beauty.png（Blender 主图：AgX、曝光 +0.26、已是显示空间）和 <标签>_glow.npy
（线性浮点的“辉光图”：只有自发光 × glowWeight），按 visual-game/glow.js 的流程合成：
  glow 半分辨率 → 亮部提取（阈值 0）→ UnrealBloomPass（5 级 mip，高斯核半径 3/5/7/9/11，strength 0.85, radius 0.4）
  → 原图 + 泛光 → 1 - exp(-x) → pow(0.8) → 加色叠回主图。
输出 <标签>_sim.png（原尺寸）、_sim960.png、_sim480.png（480×270：Boss 约占 1/4 屏的缩略），并打印“过曝”指标。
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

BLOOM_STRENGTH, BLOOM_RADIUS = 0.85, 0.4
KERNELS = (3, 5, 7, 9, 11)
FACTORS = (1.0, 0.8, 0.6, 0.4, 0.2)
BG = (0.035, 0.035, 0.050)                 # 页面底色（显示空间），战场暗色地砖的近似


def blur(a, kr):
    """three.js UnrealBloomPass 的可分离高斯：σ = 核半径 = kr，取样范围 ±kr。"""
    x = np.arange(-kr, kr + 1)
    k = np.exp(-0.5 * (x / kr) ** 2)
    k /= k.sum()
    pad = np.pad(a, ((kr, kr), (0, 0), (0, 0)), mode="edge")
    out = sum(k[i] * pad[i:i + a.shape[0]] for i in range(len(k)))
    pad = np.pad(out, ((0, 0), (kr, kr), (0, 0)), mode="edge")
    return sum(k[i] * pad[:, i:i + a.shape[1]] for i in range(len(k)))


def down2(a):
    h, w = a.shape[:2]
    a = a[:h // 2 * 2, :w // 2 * 2]
    return (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) / 4


def resize(a, size):
    """浮点图双线性缩放到 size=(宽, 高)（逐通道，PIL 的 F 模式）。"""
    chans = [np.asarray(Image.fromarray(np.ascontiguousarray(a[..., c], dtype=np.float32)).resize(size, Image.BILINEAR))
             for c in range(a.shape[2])]
    return np.stack(chans, axis=2)


def bloom(tex):
    """tex：半分辨率辉光图（线性）。返回 tex + 泛光。"""
    bright = tex * np.clip(tex.mean(axis=2, keepdims=True) / 0.01, 0, 1)
    mips, cur = [], bright
    for kr in KERNELS:
        cur = blur(down2(cur), kr)
        mips.append(cur)
    out = tex.copy()
    for m, f in zip(mips, FACTORS):
        fac = f + (1.2 - f - f) * BLOOM_RADIUS                     # lerpBloomFactor
        out += BLOOM_STRENGTH * fac * resize(m, (tex.shape[1], tex.shape[0]))
    return out


def compose(beauty, glow):
    """beauty：显示空间 0..1（H, W, 3）；glow：线性浮点（H, W, 3）。返回合成图与（泛光项）。"""
    half = down2(glow)
    tex = bloom(half)
    c = (1 - np.exp(-np.maximum(tex, 0))) ** 0.8
    c = resize(c, (beauty.shape[1], beauty.shape[0]))
    return np.clip(beauty + c, 0, 1), c


def metrics(img, W, frac=0.27):
    """Boss 所在的中央区域里的亮度分布：过曝（任一通道 > 0.97）/ 高亮（亮度 > 0.8）像素比例与平均亮度。"""
    H = img.shape[0]
    x0, x1 = int(W * (0.5 - frac * 0.62)), int(W * (0.5 + frac * 0.62))
    y0, y1 = int(H * 0.12), int(H * 0.92)
    box = img[y0:y1, x0:x1]
    lum = box @ np.array([0.2126, 0.7152, 0.0722])
    return {"blown": float((box.max(axis=2) > 0.97).mean()), "bright": float((lum > 0.8).mean()),
            "mean": float(lum.mean()), "p95": float(np.percentile(lum, 95))}


def main():
    folder, tag = Path(sys.argv[1]), sys.argv[2]
    rgba = np.asarray(Image.open(folder / f"{tag}_beauty.png").convert("RGBA"), np.float32) / 255
    # 游戏的 Boss 画在透明画布上：预乘后垫页面底色（暗色地砖），辉光再加色叠上去
    bg = np.array(BG, np.float32)[None, None, :]
    beauty = rgba[..., :3] * rgba[..., 3:4] + bg * (1 - rgba[..., 3:4])
    glow = np.load(folder / f"{tag}_glow.npy").astype(np.float32)
    final, _ = compose(beauty, glow)
    img = Image.fromarray((final * 255 + 0.5).astype(np.uint8))
    img.save(folder / f"{tag}_sim.png")
    img.resize((960, 540), Image.LANCZOS).save(folder / f"{tag}_sim960.png")
    img.resize((480, 270), Image.LANCZOS).save(folder / f"{tag}_sim480.png")
    mb = metrics(beauty, beauty.shape[1])
    mf = metrics(final, beauty.shape[1])
    print(f"SIM {tag}: before bloom blown {mb['blown']:.3%} bright {mb['bright']:.3%} mean {mb['mean']:.3f} | "
          f"after bloom blown {mf['blown']:.3%} bright {mf['bright']:.3%} mean {mf['mean']:.3f} p95 {mf['p95']:.3f}")


if __name__ == "__main__":
    main()
