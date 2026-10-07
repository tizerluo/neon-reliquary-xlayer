"""预计算当前肖像的透明留白，避免浏览器首次呈现时同步扫描像素。"""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
bounds = {}
for file in sorted((ROOT / 'visual-lab/assets/ui').glob('*.png')):
    if file.name.startswith('arena-'):
        continue
    with Image.open(file) as image:
        box = image.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox()
        x, y, right, bottom = box or (0, 0, image.width, image.height)
        bounds[file.stem] = {'width': image.width, 'height': image.height,
                            'bounds': {'x': x, 'y': y, 'width': right - x, 'height': bottom - y},
                            'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
(ROOT / 'src/ui-bounds.js').write_text('// 由 tools/ui/portrait_bounds.py 生成；肖像变化后重新运行。\n'
                                      + 'const NR_UI_BOUNDS = ' + json.dumps(bounds, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(f'Computed bounds for {len(bounds)} current portraits')
