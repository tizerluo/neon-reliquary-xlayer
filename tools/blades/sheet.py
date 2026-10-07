"""审图后处理（系统 python3 + PIL）：蜂群图缩到游戏分辨率，并拼六把并排的印样。

    python3 tools/blades/sheet.py

输入：art/review/blades/<id>-top|three-quarter.png、src/<id>-swarm-hi.png
输出：art/review/blades/<id>-swarm.png（1:1 游戏尺度，整把剑约 28 像素）、<id>-swarm-x2.png（放大两倍便于查看）、
      art/review/sheets/check-blades.png（第一行 top，第二行 three-quarter，第三行蜂群）
"""

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
REV = ROOT / "art" / "review" / "blades"
GLB = ROOT / "visual-lab" / "assets" / "blades"
IDS = ("aurelian", "mordred", "volt", "nyx", "seraph", "isolde")
CW, CH = 520, 325


def tris_of(cid):
    import struct
    data = (GLB / f"{cid}-blade.glb").read_bytes()
    clen = struct.unpack_from("<I", data, 12)[0]
    js = json.loads(data[20:20 + clen])
    t = 0
    for prim in js["meshes"][0]["primitives"]:
        t += js["accessors"][prim["indices"]]["count"] // 3
    return t


def main():
    sheet = Image.new("RGB", (CW * len(IDS), CH * 3), (8, 8, 12))
    draw = ImageDraw.Draw(sheet)
    for col, cid in enumerate(IDS):
        hi = Image.open(REV / "src" / f"{cid}-swarm-hi.png").convert("RGB")
        sw = hi.resize((hi.width // 3, hi.height // 3), Image.BOX)
        sw.save(REV / f"{cid}-swarm.png")
        sw.resize((sw.width * 2, sw.height * 2), Image.NEAREST).save(REV / f"{cid}-swarm-x2.png")
        for row, name in enumerate(("top", "three-quarter")):
            img = Image.open(REV / f"{cid}-{name}.png").convert("RGB").resize((CW, CH), Image.LANCZOS)
            sheet.paste(img, (col * CW, row * CH))
        # 蜂群：1:1 居中放进单元格（480 × 320），其余补底色
        sheet.paste(sw, (col * CW + (CW - sw.width) // 2, 2 * CH + (CH - sw.height) // 2))
        draw.text((col * CW + 8, 6), f"{cid}  {tris_of(cid)} tris", fill=(255, 220, 120))
    out = ROOT / "art" / "review" / "sheets" / "check-blades.png"
    sheet.save(out)
    print("SHEET", out, sheet.size)


if __name__ == "__main__":
    main()
