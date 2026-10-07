"""Build a versioned DeWeb program and a Cloudflare art-only bundle. No uploads."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from export_static import ROOT, runtime_assets, runtime_modules, target_name, build_html, sha

GENERATOR = 'tools/export_hybrid.py'
OUT = ROOT / 'release'


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding='utf-8')


def inventory(directory):
    return {p.relative_to(directory).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(directory.rglob('*')) if p.is_file()}


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cdn-origin', default='https://nandverse-assets.pages.dev')
    args = parser.parse_args()
    if not re.fullmatch(r'https://[a-z0-9.-]+(?::\d+)?', args.cdn_origin):
        raise ValueError('CDN origin must be an HTTPS origin without a path')
    if OUT.exists():
        prior = OUT / 'release.json'
        if not prior.is_file() or json.loads(prior.read_text()).get('generator') != GENERATOR:
            raise ValueError('release exists without this exporter manifest; refusing to replace it')
        # Previous immutable release directories stay available for rollback.
    assets, modules = runtime_assets(), runtime_modules()
    files = {p.relative_to(ROOT / 'visual-lab/assets').as_posix():
             {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(assets)}
    if len(files) != 60 or max(item['bytes'] for item in files.values()) > 25 * 1024 * 1024:
        raise ValueError('Review changed runtime asset inventory / Cloudflare file limit')
    art_version = 'art-' + stable_hash(files)[:16]
    cdn_base = args.cdn_origin + '/assets/' + art_version + '/'
    cf = OUT / 'cloudflare'
    cf_version = cf / 'assets' / art_version
    for path in sorted(assets):
        target = cf_version / path.relative_to(ROOT / 'visual-lab/assets')
        write(target, path.read_bytes())
    write(cf_version / 'asset-manifest.json', json.dumps({'version': art_version, 'files': files}, indent=2)+'\n')
    write(cf_version / 'ASSET-NOTICE.md', (ROOT / 'docs/ASSET-NOTICE.md').read_text())
    write(cf / '_headers', '''/*
  Access-Control-Allow-Origin: *
  Access-Control-Expose-Headers: Content-Length, Content-Type, ETag
  X-Content-Type-Options: nosniff
/assets/*
  Cache-Control: public, max-age=31536000, immutable
/assets/*.glb
  Content-Type: model/gltf-binary
/*
  Referrer-Policy: strict-origin-when-cross-origin
''')
    # index.html prevents Pages' SPA fallback from returning HTML for missing GLBs.
    write(cf / 'index.html', '<!doctype html><meta charset="utf-8"><title>Nandverse Assets</title><h1>Nandverse</h1><p>Neon Reliquary visual assets.</p><a href="https://1-2-231.tapekit.org/">Open Neon Reliquary</a>')
    write(cf / '404.html', '<!doctype html><meta charset="utf-8"><title>Asset not found</title><h1>Asset not found</h1>')
    for suffix in ('png', 'svg'):
        write(cf / 'tokens/oath' / ('icon-v1.' + suffix), (ROOT / 'deploy' / ('oath-icon.' + suffix)).read_bytes())

    html = build_html()
    config = {'base': cdn_base, 'version': art_version, 'files': files}
    html = html.replace('/*__NR_ASSET_CONFIG__*/ { base: null, files: {} }', json.dumps(config, separators=(',', ':')))
    # Literal CSS backgrounds and the preload are also pinned to the same art version.
    html = html.replace('visual-lab/assets/', cdn_base)
    program = {'licenses/ethers.LICENSE.md': (ROOT / 'src/vendor/ethers.LICENSE.md').read_bytes(),
               'licenses/ASSET-NOTICE.md': (ROOT / 'docs/ASSET-NOTICE.md').read_bytes()}
    for path in sorted(modules | {ROOT / 'node_modules/three/LICENSE'}):
        program[target_name(path)] = path.read_bytes()
    program_content = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                       for name, raw in sorted(program.items())}
    program_version = 'program-' + stable_hash(program_content)[:16]
    # OATH receipt/config changes produce a new HTML release while reusing all
    # byte-identical modules at their immutable shared program path.
    program_base = '../../programs/' + program_version + '/'
    html = html.replace('./vendor/', program_base + 'vendor/')
    html = html.replace('./visual-game/', program_base + 'visual-game/')
    payload = {'index.html': html.encode()}
    content = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
               for name, raw in sorted(payload.items())}
    version = 'nr-' + stable_hash({'files': content, 'programVersion': program_version})[:16]
    deweb = OUT / 'deweb'
    program_dir = deweb / 'programs' / program_version
    for name, raw in program.items():
        write(program_dir / name, raw)
    version_dir = deweb / 'releases' / version
    for name, raw in payload.items():
        write(version_dir / name, raw)
    manifest = {'version': version, 'programVersion': program_version, 'artVersion': art_version,
                'cdnBase': cdn_base, 'files': content, 'programFiles': program_content}
    write(version_dir / 'release-manifest.json', json.dumps(manifest, indent=2)+'\n')
    # The root file is activated only after every immutable program file is verified.
    launcher = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Neon Reliquary · Nandverse</title><style>body{background:#090c12;color:#bce0db;font:16px/1.8 system-ui;max-width:600px;margin:15vh auto;padding:24px}a{color:#d8bf8a}</style><h1>NEON RELIQUARY</h1><p>Opening the Nandverse expedition…</p><a id="open" href="./releases/__VERSION__/index.html">Open game</a><script>const next=new URL(document.getElementById('open').href);next.search=location.search;next.hash=location.hash;location.replace(next.href);</script></html>'''.replace('__VERSION__', version)
    write(deweb / 'index.html', launcher)
    current_deweb = {('releases/'+version+'/'+name): meta for name, meta in inventory(version_dir).items()}
    current_deweb.update({('programs/'+program_version+'/'+name): meta
                         for name, meta in program_content.items()})
    current_deweb['index.html'] = inventory(deweb)['index.html']
    release = {'generator': GENERATOR,
               'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'sourceWorkingTreeDirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
               'version': version, 'programVersion': program_version,
               'artVersion': art_version, 'cdnBase': cdn_base,
               'dewebDirectory': 'release/deweb', 'cloudflareDirectory': 'release/cloudflare',
               'runtimeAssets': len(files), 'runtimeModules': len(modules),
               'assetBytes': sum(item['bytes'] for item in files.values()),
               'dewebBytes': sum(item['bytes'] for item in current_deweb.values()),
               'dewebWrites24000': sum((item['bytes']+23999)//24000 for item in current_deweb.values()),
               'dewebFiles': current_deweb, 'cloudflareFiles': inventory(cf)}
    if max(item['bytes'] for item in current_deweb.values()) > 8_400_000:
        raise ValueError('DeWeb file exceeds the current 8,400,000 byte limit')
    write(OUT / 'release.json', json.dumps(release, indent=2)+'\n')
    print(json.dumps({key: release[key] for key in ('version','programVersion','artVersion','cdnBase','runtimeAssets','runtimeModules','assetBytes','dewebBytes','dewebWrites24000')}, indent=2))


if __name__ == '__main__':
    main()
