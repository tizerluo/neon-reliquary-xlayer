"""Boss 7 第五轮：新旧对比印样（系统 Python，需要 Pillow）。

    python3 tools/chars/_b7r5_sheets.py

输出 art/review/sheets/compare-boss-7-r4-vs-r5.png：
 行 1：game 视角 + 圣心特写（R4 | R5 | R4 | R5）
 行 2：正面整体 + 胸甲特写
 行 3：R5 圣心多角度特写
 行 4 / 5：游戏条件模拟（俯视 / 正面）——R4 无压暗（游戏临时压暗之前）| R4 + EMISSIVE_DAMP 0.5（游戏现状）| R5 无压暗 | R5 的 480×270 原尺寸
旧版审图取自 art/review/archive/boss-7-r4/review，新版取自 art/review/chars/boss-7。
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "art" / "review" / "archive" / "boss-7-r4" / "review"
NEW = ROOT / "art" / "review" / "chars" / "boss-7"
CELL = (640, 480)


def font(size):
    for p in ("/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
              "/Library/Fonts/Arial Unicode.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT = font(22)


def fit(img, size=CELL):
    """等比缩放后居中放进 size 的深色格子。"""
    img = img.convert("RGB")
    k = min(size[0] / img.width, size[1] / img.height)
    im = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)
    cell = Image.new("RGB", size, (8, 8, 12))
    cell.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return cell


def crop_boss(img, box):
    return img.crop(box)


def label(cell, text):
    d = ImageDraw.Draw(cell)
    d.rectangle((0, 0, cell.width, 32), fill=(0, 0, 0))
    d.text((8, 4), text, fill=(255, 220, 120), font=FONT)
    return cell


def shot(folder, name, text):
    p = folder / f"boss-7-{name}.png"
    if not p.exists():
        return label(Image.new("RGB", CELL, (40, 0, 0)), f"{text} (缺图 {name})")
    return label(fit(Image.open(p)), text)


def boss_box(path, margin=0.08, aspect=CELL[0] / CELL[1]):
    """按合成图里“明显高于底色”的像素求 Boss 包围盒，扩成 4:3 的裁剪框（同一行用同一个框）。"""
    m = Image.open(path).convert("RGB").point(lambda v: 255 if v > 55 else 0).convert("L")
    x0, y0, x1, y1 = m.getbbox()
    w, h = (x1 - x0) * (1 + 2 * margin), (y1 - y0) * (1 + 2 * margin)
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))


def sim_cell(name, text, box):
    p = NEW / f"boss-7-{name}.png"
    if not p.exists():
        return label(Image.new("RGB", CELL, (40, 0, 0)), f"{text} (缺图 {name})")
    return label(fit(Image.open(p).crop(box)), text)


def sim_row(view, title):
    ref = NEW / f"boss-7-sim-{view}-r5.png"
    box = boss_box(ref) if ref.exists() else (440, 170, 840, 470)
    cells = [sim_cell(f"sim-{view}-r4raw", f"R4 无压暗 {title}", box),
             sim_cell(f"sim-{view}-r4damp", f"R4 + EMISSIVE_DAMP 0.5（游戏现状）{title}", box),
             sim_cell(f"sim-{view}-r5", f"R5 无压暗 {title}", box)]
    p480 = NEW / f"boss-7-sim480-{view}-r5.png"
    c = Image.new("RGB", CELL, (8, 8, 12))
    if p480.exists():
        im = Image.open(p480).convert("RGB")
        c.paste(im, ((CELL[0] - im.width) // 2, (CELL[1] - im.height) // 2))
    cells.append(label(c, f"R5 的 480×270 原尺寸（Boss 约占 1/4 屏）{title}"))
    return cells


def main():
    rows = [
        [shot(OLD, "game", "R4 game"), shot(NEW, "game", "R5 game"), shot(OLD, "detail-core", "R4 圣心 core"),
         shot(NEW, "detail-core", "R5 圣心 core")],
        [shot(OLD, "front", "R4 front"), shot(NEW, "front", "R5 front"), shot(OLD, "detail-chest", "R4 胸甲 chest"),
         shot(NEW, "detail-chest", "R5 胸甲 chest")],
        [shot(NEW, "detail-heart-left", "R5 圣心 左侧"), shot(NEW, "detail-heart-right", "R5 圣心 右侧"),
         shot(NEW, "detail-heart-low", "R5 圣心 仰视"), shot(NEW, "detail-heart-wide", "R5 圣心 + 羽片 + 金链")],
        sim_row("top", "俯视"),
        sim_row("front", "正面"),
    ]
    sheet = Image.new("RGB", (CELL[0] * 4, CELL[1] * len(rows)), (8, 8, 12))
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            sheet.paste(cell, (c * CELL[0], r * CELL[1]))
    out = ROOT / "art" / "review" / "sheets" / "compare-boss-7-r4-vs-r5.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
