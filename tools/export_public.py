"""Allowlisted public snapshot; validate and scan before changing a destination."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from export_static import ROOT, runtime_assets

CONFIG = ROOT / 'deploy/public-export.json'
GENERATED = {'public-export-manifest.json', '.gitignore'}
PUBLIC_IGNORE = '''.DS_Store
__pycache__/
.pytest_cache/
.venv/
node_modules/
.env
.env.*
tools/.*session*.json
.qa-tmp/
research/
evidence/
art/
previews/
dist/
release/
.vercel/
.wrangler/
*.log
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sanitize(raw, evidence=False):
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw
    # User home paths are historical machine details, not product dependencies.
    text = re.sub(r'/Users/[A-Za-z0-9_.-]+/(?:Projects/NeonReliquary|Documents/ChatGPT/TapeOut)/', '', text)
    text = re.sub(r'/Users/[A-Za-z0-9_.-]+/', '~/', text)
    if evidence:
        text = re.sub(r'("(?:[A-Za-z]*Secret|clientKey|accessToken|refreshToken|sessionToken|credential)"\s*:\s*)"[^"]+"', r'\1"[redacted]"', text, flags=re.I)
    return text.encode()


def scan(files):
    problems = []
    patterns = [
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        r'\b(?:ghp_|github_pat_|sk-proj-|sk-ant-api)[A-Za-z0-9_-]{20,}',
        r'\bAKIA[0-9A-Z]{16}\b',
        r'\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b',
        r'(?:\b(?:private_key|api_key|client_secret|refresh_token)\s*[=:]\s*[\x22\x27])[A-Za-z0-9_-]{24,}',
        r'/Users/[A-Za-z0-9_.-]+/',
        r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',
    ]
    email_pattern = patterns[-1]
    vendor_blocks = {}
    for name, expected in json.loads(CONFIG.read_text()).get('vendorChecksums', {}).items():
        raw = (ROOT / name).read_bytes()
        if digest(raw) != expected:
            raise ValueError('Review changed vendor before public scanning: ' + name)
        vendor_blocks[name] = raw.decode('utf-8')
    for name, raw in files.items():
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            # Dependency licenses have upstream maintainers' public attribution.
            if '@' in pattern and ('LICENSE' in name or name.startswith('src/vendor/')):
                continue
            scanned = text
            if pattern == email_pattern:
                if name in vendor_blocks:
                    continue
                if name.endswith('.html'):
                    for block in vendor_blocks.values():
                        scanned = scanned.replace(block, '')
            matches = re.findall(pattern, scanned, flags=re.I)
            if matches:
                problems.append({'file': name, 'rule': pattern})
    # Also compare live private session credentials without displaying their values.
    secrets = set()
    for p in list((ROOT / '.qa-tmp').rglob('*.json')) + list((ROOT / 'tools').glob('.*session*.json')):
        try:
            data = json.loads(p.read_text())
        except (ValueError, OSError):
            continue
        def walk(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    if re.search('secret|token|credential|clientKey', k, re.I) and isinstance(v, str) and len(v) >= 20:
                        secrets.add(v.encode())
                    walk(v)
            elif isinstance(value, list):
                for v in value:
                    walk(v)
        walk(data)
    for name, raw in files.items():
        if any(secret in raw for secret in secrets):
            problems.append({'file': name, 'rule': 'live private credential'})
    if problems:
        raise ValueError('Public scan rejected: ' + json.dumps(problems))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--refresh-generated', action='store_true', help='Refresh only an unchanged snapshot previously written by this exporter')
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError('Destination must be outside the development repository')
    cfg = json.loads(CONFIG.read_text())
    paths = set(cfg['topLevel'] + cfg['deploymentFiles'] + cfg['historicalEvidence'])
    for tree, extensions in cfg['trees'].items():
        paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / tree).rglob('*')
                     if p.is_file() and p.suffix in extensions and not any(part.startswith('.') for part in p.relative_to(ROOT).parts)
                     and '__pycache__' not in p.parts)
    paths.update(p.relative_to(ROOT).as_posix() for p in runtime_assets())
    paths = {name for name in paths if 'SOURCE-INTEGRATION.json' not in name and 'HANDOFF' not in name}
    files = {}
    for name in sorted(paths):
        p = ROOT / cfg.get('historicalSnapshots', {}).get(name, name)
        if not p.is_file() or p.is_symlink() or ROOT not in p.resolve().parents:
            raise ValueError('Missing / unsafe allowlisted file: ' + name)
        files[name] = sanitize(p.read_bytes(), evidence=name.startswith('evidence/'))
    files['.gitignore'] = PUBLIC_IGNORE.encode()
    scan(files)
    manifest = {'schema': 'nr-public-export-v1', 'generator': 'tools/export_public.py',
                'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'allowlistSha256': digest(CONFIG.read_bytes()),
                'files': {name: {'bytes': len(raw), 'sha256': digest(raw)} for name, raw in sorted(files.items())}}
    files['public-export-manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    if (destination / '.git').exists():
        remote = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=destination, text=True).strip()
        if remote != cfg['publicRepository']:
            raise ValueError('Wrong public destination remote')
        status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=destination, text=True).strip()
        if status:
            if not args.refresh_generated:
                raise ValueError('Destination has uncommitted edits; preserve them before exporting')
            previous = json.loads((destination / 'public-export-manifest.json').read_text())
            if previous.get('schema') != 'nr-public-export-v1':
                raise ValueError('Destination is not a prior generated snapshot')
            owned = set(previous['files']) | {'public-export-manifest.json'}
            changed = set(subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=destination, text=True).splitlines())
            changed.update(subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=destination, text=True).splitlines())
            legacy = set()
            for name, expected in cfg.get('legacyDestinationFiles', {}).items():
                current = destination / name
                if current.is_file() and digest(current.read_bytes()) == expected:
                    legacy.add(name)
            if changed - owned - legacy:
                raise ValueError('Destination contains edits outside the prior export')
            for name, expected in previous['files'].items():
                current = destination / name
                if not current.is_file() or digest(current.read_bytes()) != expected['sha256']:
                    raise ValueError('Preserve destination edits before refresh: ' + name)
        old = set(subprocess.check_output(['git', 'ls-files'], cwd=destination, text=True).splitlines())
    else:
        if destination.exists() and any(destination.iterdir()):
            raise ValueError('Non-repository destination must be empty')
        old = set()
    destination.mkdir(parents=True, exist_ok=True)
    for name in old - files.keys():
        (destination / name).unlink()
    for name, raw in files.items():
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    print(json.dumps({'destination': str(destination), 'files': len(files), 'bytes': sum(map(len, files.values())),
                      'sourceCommit': manifest['sourceCommit'], 'scan': 'passed'}, indent=2))


if __name__ == '__main__':
    main()
