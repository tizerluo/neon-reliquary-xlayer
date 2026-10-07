"""Compose CUA captures of real warning progress; do not alter game assets."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NAMES = ["琉璃大教堂", "冰封档案馆", "余烬铸造厂", "零域王座"]


def compose(source, output):
    fonts = [Path('/System/Library/Fonts/Hiragino Sans GB.ttc'),
             Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')]
    font = next((ImageFont.truetype(str(p), 18) for p in fonts if p.exists()), ImageFont.load_default())
    width, height, label = 640, 360, 30

    def sheet(k):
        canvas = Image.new('RGB', (width * 2, (height + label) * 2), '#080d12')
        draw = ImageDraw.Draw(canvas)
        for stage, name in enumerate(NAMES):
            path = source / f'stage-{stage}-{k:03d}.jpg'
            with Image.open(path) as frame:
                if frame.size != (1280, 900):
                    raise ValueError(f'Expected 1280x900 screenshot: {path}')
                frame = frame.convert('RGB').crop((0, 90, 1280, 810))
                frame = frame.resize((width, height), Image.Resampling.LANCZOS)
            x, y = stage % 2 * width, stage // 2 * (height + label)
            progress = min(100, round(k / 32 * 100))
            phase = '落击 · 预警移除' if k == 33 else f'进度 {progress}% · 剩余 {100 - progress}%'
            draw.text((x + 12, y + 5), name, font=font, fill='#d2dce5')
            draw.text((x + 390, y + 5), phase, font=font, fill='#ff8293')
            canvas.paste(frame, (x, y + label))
        return canvas

    output.mkdir(parents=True, exist_ok=True)
    sheet(16).save(output / 'four-arenas-progress.jpg', quality=93)
    frames = [sheet(k) for k in range(34)]
    frames[0].save(output / 'warning-progress.webp', save_all=True, append_images=frames[1:],
                   duration=125, loop=0, quality=84, method=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('captures', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    compose(args.captures, args.output)
