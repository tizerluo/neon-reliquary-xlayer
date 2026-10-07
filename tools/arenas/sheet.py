"""审图印样（系统 python3 + PIL）：把 art/review/arenas/<区域>/ 里的审图拼成 art/review/sheets/check-arena-<区域>.png。

    python3 tools/arenas/sheet.py [区域id]        # 默认 cathedral

分区：Blender 游戏机位（含占位人形 + 红色预警圈）/ 真实引擎里的游戏机位（three.js，同一套灯光 + ACES + 辉光 + 暗角，preview.html 抓的）/
整体俯视与斜视 / 地面贴图细节、纹章、北侧布景近景。缺图的格子留黑并写“(缺)”。
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
BG = (8, 9, 13)
FONT_FILES = ("/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/Songti.ttc")


def font(size=15):
    """能显示中文的字体（macOS 自带）；找不到就退回 PIL 默认字体（中文会变方块，但不影响看图）。"""
    for f in FONT_FILES:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()
FG = (255, 220, 120)
LAB = (170, 200, 215)


def load(path, size):
    """等比缩放放进 size 的格子（居中）。"""
    cell = Image.new("RGB", size, (20, 22, 28))
    if not Path(path).exists():
        ImageDraw.Draw(cell).text((10, 10), f"(缺) {Path(path).name}", fill=(220, 90, 90), font=font())
        return cell
    im = Image.open(path).convert("RGB")
    s = min(size[0] / im.width, size[1] / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    cell.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return cell


def main(rid="cathedral"):
    rev = ROOT / "art" / "review" / "arenas" / rid
    from arenas import verify
    r = verify.check(rid)
    W = 1920
    rows = []       # (标题, [(文件名, 标签, (w, h))...])
    game = (640, 360)
    names = [("center", "中心"), ("north", "北边界"), ("east", "东边界"), ("south", "南边界"), ("west", "西边界"), ("northwest", "西北角")]
    rows.append(("Blender Cycles · 游戏机位（正交 / 俯角 51° / 视宽 36 / 16:9；灰色胶囊 2.3 m + 红色预警圈）",
                 [(f"game-{n}.png", f"game-{n}  {zh}", game) for n, zh in names[:3]]))
    rows.append(("", [(f"game-{n}.png", f"game-{n}  {zh}", game) for n, zh in names[3:]]))
    rows.append(("真实引擎（three.js，arena-env.js 同一套灯光 / ACES / 辉光 / 暗角 / 雾）· 游戏机位",
                 [(f"three-game-{n}.png", f"three-game-{n}  {zh}", game) for n, zh in names[:3]]))
    rows.append(("", [(f"three-game-{n}.png", f"three-game-{n}  {zh}", game) for n, zh in names[3:]]))
    rows.append(("整体：俯视 150 × 141 m（含边界布景）/ 斜视（引擎）",
                 [("overview.png", "overview（Blender 俯视）", (720, 720)), ("three-overview-oblique.png", "three-overview-oblique（引擎）", (1200, 675))]))
    rows.append(("近景：北侧布景（Blender 斜视 / 引擎斜视）",
                 [("bounds-north.png", "bounds-north（Blender）", (960, 540)), ("three-free-bn.png", "three-free-bn（引擎）", (960, 540))]))
    if rid == "cathedral":
        rows.append(("近景：北侧低机位 / 玫瑰窗残骸（引擎）",
                     [("bounds-north-low.png", "bounds-north-low（Blender）", (960, 540)), ("three-free-rose.png", "three-free-rose（引擎）", (960, 540))]))
    else:
        rows.append(("近景：北侧低机位（Blender / 引擎）",
                     [("bounds-north-low.png", "bounds-north-low（Blender）", (960, 540)), ("three-free-bnl.png", "three-free-bnl（引擎）", (960, 540))]))
    rows.append(("地面：贴图近景 / 12 m 周期俯视 / 地面纹章" if rid == "cathedral" else "地面：贴图近景 / 12 m 视野俯视 / 地面纹章",
                 [("floor-detail.png", "floor-detail", (960, 540)), ("floor-topdown.png", "floor-topdown（12 m 视野）" if rid != "cathedral" else "floor-topdown（12 m）", (480, 480)),
                  ("emblem-topdown.png", "emblem-topdown（30 m）", (480, 480))]))
    # 逐行排版
    head = 70
    y = head
    placed = []
    for title, cells in rows:
        th = 26 if title else 8
        h = max(c[2][1] for c in cells) + 22
        placed.append((y, title, th, cells))
        y += th + h + 6
    sheet = Image.new("RGB", (W, y), BG)
    d = ImageDraw.Draw(sheet)
    F = font(15)
    g = r["groups"]
    d.text((10, 8), f"arena {rid}   {r['bytes'] / 1048576:.2f} MB   {r['tris']} tris (floor {g['ARENA_FLOOR']['tris']} / bounds {g['ARENA_BOUNDS']['tris']} / props "
           f"{g['ARENA_PROPS']['tris']} / lights {g['ARENA_LIGHTS']['tris']})   meshes {r['meshes']}  prims {r['prims']}  materials {len(r['mats'])}", fill=FG, font=F)
    d.text((10, 26), "textures: " + "  ".join(f"{im['name']} {im['w']}x{im['h']} {im['bytes'] // 1024}KB" for im in r["imgs"]), fill=LAB, font=F)
    d.text((10, 44), "VERIFY " + ("OK" if not r["problems"] else "FAIL: " + "; ".join(r["problems"])), fill=(120, 230, 160) if not r["problems"] else (240, 100, 100), font=F)
    for (yy, title, th, cells) in placed:
        if title:
            d.text((10, yy + 6), title, fill=FG, font=F)
        x = 0
        for (fn, label, size) in cells:
            sheet.paste(load(rev / fn, size), (x, yy + th))
            d.text((x + 8, yy + th + 4), label, fill=(255, 255, 255), font=F)
            x += size[0]
    out = ROOT / "art" / "review" / "sheets" / f"check-arena-{rid}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("SHEET", out, sheet.size, f"{out.stat().st_size / 1048576:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cathedral")
