"""Compose real-game CUA captures; never generate or modify accepted game assets."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NAMES = ["余烬之王 · 火焰扇", "苍白巨龙 · 冰螺旋", "钢铁巨兽 · 冲击波", "空壳元帅 · 亡灵阵",
         "机械神祇 · 交叉光束", "零域先知 · 虚空井", "剧毒三位体 · 毒池", "灰烬炽天使 · 羽刃风暴"]


def compose(source, output):
    fonts = [Path('/System/Library/Fonts/Hiragino Sans GB.ttc'), Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')]
    font = next((ImageFont.truetype(str(p), 16) for p in fonts if p.exists()), ImageFont.load_default())
    width, height, label = 480, 270, 26

    def sheet(paths, caption=None):
        out = Image.new('RGB', (width * 2, (height + label) * 4), '#080d12')
        d = ImageDraw.Draw(out)
        for boss, path in enumerate(paths):
            im = Image.open(path).convert('RGB')
            if im.size != (1280, 900):
                raise ValueError(f'Expected fixed 1280×900 capture: {path}')
            # Only trim the browser page's letterbox; retain the complete 1280×720 game and HUD.
            im = im.crop((0, 90, 1280, 810)).resize((width, height), Image.Resampling.LANCZOS)
            x, y = boss % 2 * width, boss // 2 * (height + label)
            d.text((x + 10, y + 4), NAMES[boss], fill='#cbd8e3', font=font)
            if caption is not None:
                d.text((x + width - 62, y + 4), f'{caption:.2f}s', fill='#8396ab', font=font)
            out.paste(im, (x, y + label))
        return out

    output.mkdir(parents=True, exist_ok=True)
    still = sheet([output / f'boss-{b}-normal.jpg' for b in range(8)])
    still.save(output / 'eight-bosses-in-game.jpg', quality=93)
    frames = [sheet([source / f'boss-{b}-{k:03d}.jpg' for b in range(8)], k / 8) for k in range(49)]
    frames[0].save(output / 'eight-boss-attacks.webp', save_all=True, append_images=frames[1:],
                   duration=125, loop=0, quality=83, method=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('captures', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    compose(args.captures, args.output)
