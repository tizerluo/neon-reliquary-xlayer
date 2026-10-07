"""Boss 6 毒雾特效轮：新旧对比印样与更新后的总览印样（系统 Python，需要 Pillow）。

    python3 tools/chars/_b6fx_sheets.py

输出：
  art/review/sheets/compare-boss-6-fx.png  每行 旧 | 新 成对排列
    行 1：Attack 14 三束毒雾扇面特写（3/4 机位） / Attack 14 game 俯视（取景贴合角色）
    行 2：Attack 14 俯视特写 / Attack 14 中首毒雾侧视（雾团层次 + 毒滴）
    行 3：Attack 21 扫射扇面特写 / Attack 14 中首喷口特写（雾根）
    行 4：竖幅整体：待机正面、待机四分之三、Attack 12 起喷
  art/review/sheets/check-boss-6.png  总览：待机五视角 + 动作帧 + 毒雾特写
旧版取自 art/review/archive/boss-6-prefx（review 为原审图，review-fx 为用同一机位补拍的旧版特写），
新版取自 art/review/chars/boss-6。
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "art" / "review" / "archive" / "boss-6-prefx"
NEW = ROOT / "art" / "review" / "chars" / "boss-6"


def font(size):
    for p in ("/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
              "/Library/Fonts/Arial Unicode.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT = font(20)
SMALL = font(15)


def fit(img, size):
    """等比缩放后居中放进 size 的深色格子。"""
    img = img.convert("RGB")
    k = min(size[0] / img.width, size[1] / img.height)
    im = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)
    cell = Image.new("RGB", size, (8, 8, 12))
    cell.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return cell


def tag(cell, text, new, font_=FONT, h=30):
    d = ImageDraw.Draw(cell)
    col = (120, 255, 170) if new else (255, 170, 120)
    d.rectangle((0, 0, cell.width, h), fill=(0, 0, 0))
    d.text((8, 4), text, fill=col, font=font_)
    return cell


def pair(name_old, name_new, size, title, small=False):
    po = OLD / name_old
    pn = NEW / name_new
    f, h = (SMALL, 24) if small else (FONT, 30)
    return [tag(fit(Image.open(po), size), f"旧 实心薄片 · {title}", False, f, h),
            tag(fit(Image.open(pn), size), f"新 半透明毒雾 · {title}", True, f, h)]


def row(cells):
    w = sum(c.width for c in cells)
    r = Image.new("RGB", (w, cells[0].height), (8, 8, 12))
    x = 0
    for c in cells:
        r.paste(c, (x, 0))
        x += c.width
    return r


def stack(rows):
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height for r in rows)), (8, 8, 12))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    return sheet


def compare():
    L = (640, 480)
    P = (320, 480)
    fx = "review-fx/boss-6-"
    rows = [
        row(pair(fx + "attack14-detail-fx.png", "boss-6-attack14-detail-fx.png", L, "Attack 14 扇面") +
            pair(fx + "attack14-game.png", "boss-6-attack14-game.png", L, "Attack 14 game")),
        row(pair(fx + "attack14-detail-top.png", "boss-6-attack14-detail-top.png", L, "Attack 14 俯视特写") +
            pair(fx + "attack14-detail-mist.png", "boss-6-attack14-detail-mist.png", L, "单束毒雾侧视")),
        row(pair(fx + "attack21-detail-fx.png", "boss-6-attack21-detail-fx.png", L, "Attack 21 扫射") +
            pair(fx + "attack14-detail-mouth.png", "boss-6-attack14-detail-mouth.png", L, "喷口 / 雾根")),
        row(pair(fx + "front.png", "boss-6-front.png", P, "front", True) +
            pair(fx + "three-quarter.png", "boss-6-three-quarter.png", L, "3/4") +
            pair(fx + "attack12-detail-fx.png", "boss-6-attack12-detail-fx.png", P, "Attack 12 起喷", True)),
    ]
    sheet = stack(rows)
    out = ROOT / "art" / "review" / "sheets" / "compare-boss-6-fx.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out, sheet.size)


def overview():
    """15 格总览（5 列 × 3 行，每格 400×480，左上角标文件名）。"""
    names = [
        "boss-6-front.png", "boss-6-three-quarter.png", "boss-6-rear.png", "boss-6-side.png", "boss-6-top.png",
        "boss-6-move5-three-quarter.png", "boss-6-attack14-three-quarter.png", "boss-6-enrage24-three-quarter.png",
        "boss-6-attack14-game.png", "boss-6-game.png",
        "boss-6-attack14-detail-fx.png", "boss-6-attack14-detail-mist.png", "boss-6-attack14-detail-top.png",
        "boss-6-attack21-detail-fx.png", "boss-6-attack14-detail-mouth.png",
    ]
    cell = (400, 480)
    cells = []
    for n in names:
        c = fit(Image.open(NEW / n), cell)
        d = ImageDraw.Draw(c)
        d.text((6, 4), n, fill=(255, 210, 120), font=SMALL)
        cells.append(c)
    rows = [row(cells[i:i + 5]) for i in range(0, len(cells), 5)]
    sheet = stack(rows)
    out = ROOT / "art" / "review" / "sheets" / "check-boss-6.png"
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    compare()
    overview()
