"""Boss 0 特效轮：新旧对比印样（系统 Python，需要 Pillow）。

    python3 tools/chars/_b0fx_sheets.py

输出 art/review/sheets/compare-boss-0-fx.png：每行 旧 | 新 成对排列
 行 1：Enrage（咆哮）game 俯视 / 游戏机位——王冠与炉墙火焰爆燃
 行 2：待机 game 俯视 + Enrage 特效特写（王冠 + 炉墙顶）
 行 3：待机特效特写 + 塔顶喷口特写
 行 4：竖幅整体：正面、四分之三、Enrage 四分之三、Attack 四分之三
旧版取自 art/review/archive/boss-0-prefx（review 为原审图，review-fx 为用同一机位补拍的旧版特写），
新版取自 art/review/chars/boss-0。
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "art" / "review" / "archive" / "boss-0-prefx"
NEW = ROOT / "art" / "review" / "chars" / "boss-0"


def font(size):
    for p in ("/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
              "/Library/Fonts/Arial Unicode.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT = font(20)
SMALL = font(16)


def fit(img, size):
    """等比缩放后居中放进 size 的深色格子。"""
    img = img.convert("RGB")
    k = min(size[0] / img.width, size[1] / img.height)
    im = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)
    cell = Image.new("RGB", size, (8, 8, 12))
    cell.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return cell


def tag(cell, text, new):
    d = ImageDraw.Draw(cell)
    col = (120, 255, 170) if new else (255, 170, 120)
    d.rectangle((0, 0, cell.width, 30), fill=(0, 0, 0))
    d.text((8, 4), text, fill=col, font=FONT)
    return cell


def pair(name_old, name_new, size, title):
    po = OLD / name_old
    pn = NEW / name_new
    return [tag(fit(Image.open(po), size), f"旧 实心锥体 · {title}", False),
            tag(fit(Image.open(pn), size), f"新 半透明火舌 · {title}", True)]


def row(cells):
    w = sum(c.width for c in cells)
    r = Image.new("RGB", (w, cells[0].height), (8, 8, 12))
    x = 0
    for c in cells:
        r.paste(c, (x, 0))
        x += c.width
    return r


def main():
    L = (640, 480)
    P = (320, 480)
    rows = [
        row(pair("review-fx/boss-0-enrage28-game.png", "boss-0-enrage28-game.png", L, "Enrage 28 game") +
            pair("review-fx/boss-0-enrage24-game.png", "boss-0-enrage24-game.png", L, "Enrage 24 game")),
        row(pair("review-fx/boss-0-game.png", "boss-0-game.png", L, "Idle game") +
            pair("review-fx/boss-0-enrage28-detail-fx.png", "boss-0-enrage28-detail-fx.png", L, "Enrage 28 特写")),
        row(pair("review-fx/boss-0-detail-fx.png", "boss-0-detail-fx.png", L, "Idle 特写") +
            pair("review-fx/boss-0-detail-vent.png", "boss-0-detail-vent.png", L, "塔顶喷口")),
        row(pair("review/boss-0-front.png", "boss-0-front.png", P, "front") +
            pair("review/boss-0-three-quarter.png", "boss-0-three-quarter.png", P, "3/4") +
            pair("review/boss-0-enrage28-three-quarter.png", "boss-0-enrage28-three-quarter.png", P, "Enrage 28") +
            pair("review/boss-0-attack18-three-quarter.png", "boss-0-attack18-three-quarter.png", P, "Attack 18")),
    ]
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height for r in rows)), (8, 8, 12))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    out = ROOT / "art" / "review" / "sheets" / "compare-boss-0-fx.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
