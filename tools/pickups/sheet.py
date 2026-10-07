"""审图后处理（系统 python3 + PIL）：游戏机位总览缩到 1:1 的游戏分辨率，并拼印样 check-pickups.png。

    python3 tools/pickups/sheet.py

输入：art/review/pickups/ 下 <id>-front|three-quarter|top.png、chest-open.png、chest-halo.png、src/game-scale-hi.png
输出：game-scale.png（640×360，1 米 ≈ 36 像素，即 720p 游戏画面里的实际大小）、game-scale-x2.png（最近邻放大两倍便于查看）、
      art/review/sheets/check-pickups.png（上三行：碎片 / 圣瓶 / 圣物匣 × front / three-quarter / top；
      第四行：圣物匣开盖 + 光环特写 + 游戏机位局部放大；底部整幅游戏机位 ×2）
"""

import json
import struct
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
REV = ROOT / "art" / "review" / "pickups"
GLB = ROOT / "visual-lab" / "assets" / "pickups"
IDS = ("shard", "vial", "chest")
CW, CH = 520, 325


def tris_of(pid):
    data = (GLB / f"{pid}.glb").read_bytes()
    clen = struct.unpack_from("<I", data, 12)[0]
    js = json.loads(data[20:20 + clen])
    return sum(js["accessors"][p["indices"]]["count"] // 3 for m in js["meshes"] for p in m["primitives"])


def main():
    hi = Image.open(REV / "src" / "game-scale-hi.png").convert("RGB")
    ss = hi.width // 640
    game = hi.resize((hi.width // ss, hi.height // ss), Image.BOX)
    game.save(REV / "game-scale.png")
    game.resize((game.width * 2, game.height * 2), Image.NEAREST).save(REV / "game-scale-x2.png")

    W = CW * 3
    sheet = Image.new("RGB", (W, CH * 4 + game.height * 2), (8, 8, 12))
    draw = ImageDraw.Draw(sheet)
    for col, pid in enumerate(IDS):
        for row, name in enumerate(("front", "three-quarter", "top")):
            img = Image.open(REV / f"{pid}-{name}.png").convert("RGB").resize((CW, CH), Image.LANCZOS)
            sheet.paste(img, (col * CW, row * CH))
        draw.text((col * CW + 8, 6), f"{pid}  {tris_of(pid)} tris", fill=(255, 220, 120))
    for col, name in enumerate(("chest-open", "chest-halo")):
        img = Image.open(REV / f"{name}.png").convert("RGB").resize((CW, CH), Image.LANCZOS)
        sheet.paste(img, (col * CW, 3 * CH))
    draw.text((8, 3 * CH + 6), "chest open: CHEST_LID rotation.x = -110 deg", fill=(255, 220, 120))
    draw.text((CW + 8, 3 * CH + 6), "chest halo close-up", fill=(255, 220, 120))
    # 第四行第三格：游戏机位局部（中心 CW×CH 区域 ×1，近似 1:1 对照 + 放大）
    crop = game.crop((game.width // 2 - 130, game.height // 2 - 80, game.width // 2 + 130, game.height // 2 + 80)).resize((CW, CH), Image.NEAREST)
    sheet.paste(crop, (2 * CW, 3 * CH))
    draw.text((2 * CW + 8, 3 * CH + 6), "game scale center crop (x2)", fill=(255, 220, 120))
    sheet.paste(game.resize((game.width * 2, game.height * 2), Image.NEAREST), ((W - game.width * 2) // 2, 4 * CH))
    draw.text((8, 4 * CH + 6), "game scale 1280x720 (x2 of 640x360; 36 px / m)", fill=(255, 220, 120))
    out = ROOT / "art" / "review" / "sheets" / "check-pickups.png"
    sheet.save(out)
    print("SHEET", out, sheet.size)


if __name__ == "__main__":
    main()
