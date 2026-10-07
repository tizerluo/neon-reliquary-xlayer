"""Boss 4 光束特效轮：新旧对比印样与更新后的总览印样（系统 Python，需要 Pillow）。

    python3 tools/chars/_b4fx_sheets.py

输出：
  art/review/sheets/compare-boss-4-fx.png  每行 旧 | 新 成对排列
    行 1：Attack 14 光束扇面特写（3/4 机位） / Attack 14 game 俯视（取景贴合角色）
    行 2：Attack 14 俯视特写 / Attack 14 单根光束侧视（芯线 + 光晕 + 脉冲环）
    行 3：Attack 18 game 俯视 / Enrage 24 炮口光晕特写
    行 4：竖幅整体：待机正面、待机四分之三、Attack 11（蓄能）、Attack 14（齐射）
  art/review/sheets/check-boss-4.png  总览：待机六视角 + 动作帧 + 特效特写
旧版取自 art/review/archive/boss-4-prefx（review 为原审图，review-fx 为用同一机位补拍的旧版特写），
新版取自 art/review/chars/boss-4。
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "art" / "review" / "archive" / "boss-4-prefx"
NEW = ROOT / "art" / "review" / "chars" / "boss-4"


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
    return [tag(fit(Image.open(po), size), f"旧 实心光束 · {title}", False),
            tag(fit(Image.open(pn), size), f"新 能量光束 · {title}", True)]


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
    fx = "review-fx/boss-4-"
    rows = [
        row(pair(fx + "attack14-detail-fx.png", "boss-4-attack14-detail-fx.png", L, "Attack 14 扇面") +
            pair(fx + "attack14-game.png", "boss-4-attack14-game.png", L, "Attack 14 game")),
        row(pair(fx + "attack14-detail-top.png", "boss-4-attack14-detail-top.png", L, "Attack 14 俯视特写") +
            pair(fx + "attack14-detail-beam.png", "boss-4-attack14-detail-beam.png", L, "单根光束侧视")),
        row(pair(fx + "attack18-game.png", "boss-4-attack18-game.png", L, "Attack 18 game") +
            pair(fx + "enrage24-detail-muzzle.png", "boss-4-enrage24-detail-muzzle.png", L, "Enrage 24 炮口")),
        row(pair("review/boss-4-front.png", "boss-4-front.png", P, "front") +
            pair("review/boss-4-three-quarter.png", "boss-4-three-quarter.png", P, "3/4") +
            pair(fx + "attack11-three-quarter.png", "boss-4-attack11-three-quarter.png", P, "Attack 11 蓄能") +
            pair(fx + "attack14-three-quarter.png", "boss-4-attack14-three-quarter.png", P, "Attack 14 齐射")),
    ]
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height for r in rows)), (8, 8, 12))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    out = ROOT / "art" / "review" / "sheets" / "compare-boss-4-fx.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
