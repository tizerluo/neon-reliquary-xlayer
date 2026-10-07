"""把多个角色的审图拼成一张接触印样，便于成组验收。

    python3 tools/contact_sheet.py 输出名 单元格高度 id:视角,视角 [id:视角 ...] [-- 下一行 ...]

视角写审图文件名去掉 "<id>-" 与 ".png" 的部分（如 three-quarter、move5-three-quarter）；
缺失时依次尝试 geo- 前缀版本，仍缺则留黑格。输出到 art/review/sheets/<输出名>.png。
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "art" / "review" / "chars"


def cell(cid, view, height):
    """读取一张审图并缩放到统一高度；找不到时返回黑格。"""
    for name in (f"{cid}-{view}.png", f"{cid}-geo-{view}.png"):
        path = REVIEW / cid / name
        if path.exists():
            img = Image.open(path).convert("RGB")
            return img.resize((int(img.width * height / img.height), height), Image.LANCZOS), name
    return Image.new("RGB", (int(height * 0.75), height), (20, 0, 0)), f"{cid}-{view} (missing)"


def main():
    out_name, height = sys.argv[1], int(sys.argv[2])
    # 参数 "--" 换行；同一行内可以连续放多个角色
    rows = [[]]
    for spec in sys.argv[3:]:
        if spec == "--":
            rows.append([])
            continue
        cid, views = spec.split(":")
        rows[-1].extend(cell(cid, v, height) for v in views.split(","))
    rows = [row for row in rows if row]
    width = max(sum(img.width for img, _ in row) for row in rows)
    sheet = Image.new("RGB", (width, height * len(rows)), (8, 8, 12))
    draw = ImageDraw.Draw(sheet)
    for r, row in enumerate(rows):
        x = 0
        for img, label in row:
            sheet.paste(img, (x, r * height))
            draw.text((x + 6, r * height + 4), label, fill=(255, 220, 120))
            x += img.width
    out = ROOT / "art" / "review" / "sheets" / f"{out_name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
