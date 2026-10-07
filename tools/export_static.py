"""导出当前高清游戏的独立静态站；不重建美术、不改本地游戏入口。"""
import ast
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
ASSETS = ROOT / 'visual-lab/assets'
GENERATOR = 'tools/export_static.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(path):
    if not path.is_file():
        raise ValueError(f'Missing runtime file: {path.relative_to(ROOT)}')
    # 本地 APFS 不区分大小写，线上 Linux 区分；发布前逐段核对。
    current = ROOT
    for name in path.relative_to(ROOT).parts:
        if name not in {child.name for child in current.iterdir()}:
            raise ValueError(f'Case mismatch: {path.relative_to(ROOT)}')
        current /= name
    return path


def runtime_assets():
    # 裁切元数据与图片一起验真，防止更新肖像后发布过时的构图边界。
    source = (ROOT / 'src/ui-bounds.js').read_text()
    bounds = json.loads(re.search(r'const NR_UI_BOUNDS = (\{.*\});', source)[1])
    for name, meta in bounds.items():
        if sha(ASSETS / 'ui' / f'{name}.png') != meta['sha256']:
            raise ValueError(f'Stale portrait bounds: {name}; run tools/ui/portrait_bounds.py')
    presentation = (ROOT / 'visual-game/presentation.mjs').read_text()
    heroes = re.findall(r"\{ id: '([^']+)', glb: '([^']+)'", presentation)
    if len(heroes) != 6:
        raise ValueError('Expected six hero definitions; review the export inventory')
    arena_source = (ROOT / 'visual-game/arena-env.js').read_text()
    regions = ast.literal_eval(re.search(r'export const ARENAS = (\[[^;]+\]);', arena_source)[1])
    pickup_source = (ROOT / 'visual-game/roster-bridge.js').read_text()
    pickups = ast.literal_eval(re.search(r'const PICKUP_KEYS = (\[[^;]+\]);', pickup_source)[1])
    files = {ASSETS / glb for _, glb in heroes}
    files.update(ASSETS / 'blades' / f'{hero}-blade.glb' for hero, _ in heroes)
    for prefix, count in [('boss', 8), ('mob', 8), ('elite', 6)]:
        files.update(ASSETS / 'chars' / f'{prefix}-{i}-game.glb' for i in range(count))
    files.update(ASSETS / 'arenas' / f'{region}.glb' for region in regions)
    files.update(ASSETS / 'pickups' / f'{key.removeprefix("pickup-")}.glb' for key in pickups)
    files.update(path for path in (ASSETS / 'ui').rglob('*') if path.is_file())
    for path in files:
        require(path)
        if path.suffix != '.glb':
            continue
        raw = path.read_bytes()
        length, kind = struct.unpack_from('<II', raw, 12)
        if raw[:4] != b'glTF' or kind != 0x4E4F534A:
            raise ValueError(f'Invalid GLB: {path.name}')
        gltf = json.loads(raw[20:20 + length])
        # 当前发布模型的纹理都嵌在 GLB 中；出现外链时必须补充清单。
        for group in ('buffers', 'images'):
            for item in gltf.get(group, []):
                uri = item.get('uri')
                if uri and not uri.startswith('data:'):
                    raise ValueError(f'Unlisted GLB dependency: {path.name}: {uri}')
    return files


def runtime_modules():
    files = {p for p in (ROOT / 'visual-game').rglob('*') if p.suffix in ('.js', '.mjs')}
    pending = list(files)
    while pending:
        path = pending.pop()
        source = path.read_text()
        imports = set(re.findall(r'(?:import|export)\s+(?:[^;]*?\s+from\s+)?[\x22\x27]([^\x22\x27]+)[\x22\x27]', source))
        imports.update(re.findall(r'import\s*\(\s*[\x22\x27]([^\x22\x27]+)[\x22\x27]', source))
        for spec in imports:
            if spec == 'three':
                dependency = ROOT / 'node_modules/three/build/three.module.js'
            elif spec.startswith('three/addons/'):
                dependency = ROOT / 'node_modules/three/examples/jsm' / spec.removeprefix('three/addons/')
            elif spec.startswith('.'):
                dependency = (path.parent / spec).resolve()
            else:
                raise ValueError(f'Unmapped import: {path.name}: {spec}')
            require(dependency)
            if dependency not in files:
                files.add(dependency)
                pending.append(dependency)
    return files


def target_name(path):
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith('node_modules/three/'):
        return 'vendor/three/' + rel.removeprefix('node_modules/three/')
    return rel


def build_html():
    # 在临时目录复用已验证的原构建，避免改正在验收的本地 HTML。
    with tempfile.TemporaryDirectory(prefix='nr-static-html-') as directory:
        temp = Path(directory)
        shutil.copy2(ROOT / 'build.py', temp / 'build.py')
        shutil.copytree(ROOT / 'src', temp / 'src')
        (temp / 'deploy').mkdir()
        shutil.copy2(ROOT / 'deploy/oath.json', temp / 'deploy/oath.json')
        subprocess.run(['python3', 'build.py'], cwd=temp, check=True, capture_output=True)
        html = (temp / 'Neon_Reliquary_v3.html').read_text()
    match = re.search(r'<script type="importmap">(.*?)</script>', html)
    imports = json.loads(match[1])
    imports['imports']['three'] = './vendor/three/build/three.module.js'
    imports['imports']['three/addons/'] = './vendor/three/examples/jsm/'
    return html[:match.start(1)] + json.dumps(imports, separators=(',', ':')) + html[match.end(1):]


def main():
    assets, modules = runtime_assets(), runtime_modules()
    files = assets | modules | {require(ROOT / 'node_modules/three/LICENSE')}
    html = build_html()
    prior_link = None
    if OUT.exists():
        manifest = OUT / 'deployment-manifest.json'
        if not manifest.is_file() or json.loads(manifest.read_text()).get('generator') != GENERATOR:
            raise ValueError('dist exists without this exporter manifest; refusing to replace it')
        link = OUT / '.vercel/project.json'
        if link.is_file():
            prior_link = link.read_bytes()
    with tempfile.TemporaryDirectory(prefix='.static-export-', dir=ROOT) as directory:
        temp = Path(directory)
        for path in sorted(files):
            target = temp / target_name(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        for name in ('index.html', 'Neon_Reliquary_v3.html'):
            (temp / name).write_text(html)
        licenses = temp / 'licenses'
        licenses.mkdir()
        shutil.copy2(ROOT / 'src/vendor/ethers.LICENSE.md', licenses / 'ethers.LICENSE.md')
        shutil.copy2(ROOT / 'deploy/vercel.json', temp / 'vercel.json')
        (temp / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
        staged = sorted(p for p in temp.rglob('*') if p.is_file())
        manifest = {
            'generator': GENERATOR,
            'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'sourceWorkingTreeDirty': bool(subprocess.check_output(
                ['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
            'sourceHtmlSha256': sha(ROOT / 'Neon_Reliquary_v3.html'),
            'exportedHtmlSha256': sha(temp / 'index.html'),
            'exporterSha256': sha(Path(__file__)),
            'runtimeAssets': len(assets),
            'runtimeModules': len(modules),
            'scope': 'Current default HD game and native fallback; historical knight/full-Nyx showcase assets are excluded.',
            'files': {p.relative_to(temp).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in staged},
        }
        (temp / 'deployment-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        upload_bytes = sum(p.stat().st_size for p in temp.rglob('*') if p.is_file())
        if upload_bytes >= 100_000_000:
            raise ValueError(f'Export exceeds the 100 MB CLI upload budget: {upload_bytes}')
        if OUT.exists():
            shutil.rmtree(OUT)
        shutil.copytree(temp, OUT)
    if prior_link:
        (OUT / '.vercel').mkdir()
        (OUT / '.vercel/project.json').write_bytes(prior_link)
    print(f'Exported {OUT}: {upload_bytes / 1e6:.3f} MB; {len(assets)} assets, {len(modules)} modules')


if __name__ == '__main__':
    main()
