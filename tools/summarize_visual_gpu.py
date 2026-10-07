#!/usr/bin/env python3
"""核验浏览器真实 GPU 原始记录，生成汇总；不改游戏或历史验收数据。"""
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/visual-evidence/final-gpu-2026-10-04'
LAYERS = ('native', 'arena', 'roster')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(values, p):
    a = sorted(values)
    return a[max(0, math.ceil(len(a) * p) - 1)]


def main():
    reports = []
    for path in sorted(OUT.glob('*.json')):
        data = json.loads(path.read_text())
        if isinstance(data, dict) and isinstance(data.get('rows'), list):
            assert data['valid'] and data['disjoint'] == 0 and not data['errors'], path.name
            rows = data['rows']
            assert len(rows) == data['requested'] and [r['index'] for r in rows] == list(range(len(rows))), path.name
            for row in rows:
                assert row['order'] == list(LAYERS), (path.name, row['index'])
                assert all(math.isfinite(row['gpuNs'][k]) and row['gpuNs'][k] > 0 for k in LAYERS), path.name
            sums = [sum(row['gpuNs'][k] for k in LAYERS) / 1e6 for row in rows]
            for key, p in [('median', .5), ('p95', .95), ('p99', .99)]:
                assert abs(quantile(sums, p) - data['totalGpuMs'][key]) < 1e-9, (path.name, key)
                for layer in LAYERS:
                    values = [row['gpuNs'][layer] / 1e6 for row in rows]
                    assert abs(quantile(values, p) - data['gpuMs'][layer][key]) < 1e-9, (path.name, layer, key)
            assert not data['snapshot']['errors'] and not data['snapshot']['renderer']['errors'], path.name
            assert data['metrics']['error'] is None and data['metrics']['env']['error'] is None, path.name
            assert not data['metrics']['env']['atmosphereErrors'] and not data['metrics']['reflections']['errors'], path.name
            reports.append(data)
    assert len(reports) == 40 and sum(len(r['rows']) for r in reports) == 10080
    boss = [r for r in reports if r['label'].startswith('boss-')]
    assert len(boss) == 16
    assert sum(len(r['scenario']['triggered']) for r in boss) == 48
    assert all([t['sequence'] for t in r['scenario']['triggered']] == [0, 1, 2] for r in boss)
    assert len([r for r in reports if r['label'].startswith('hero-')]) == 12
    cleanup = json.loads((OUT / 'cleanup.json').read_text())
    end = cleanup['after']
    assert end['restored'] and end['created'] == end['deleted'] == 30240 and end['liveQueries'] == 0
    assert not any(end['activeQueries']) and not any(end['glErrors']) and not end['errors'] and end['invalidated'] == 0
    assert cleanup['pool'] == [] and cleanup['qaTabClosed'] and cleanup['qaViewportCleared']
    assert cleanup['player']['testAPIAbsent'] and cleanup['player']['gpuProbeAbsent'] and cleanup['player']['gpuRefsAbsent']
    hashes = json.loads((OUT / 'browser-source-hashes.json').read_text())
    browser_changed = [item['path'] for item in hashes if digest(ROOT / item['path']) != item['sha256']]
    assert not browser_changed, browser_changed
    preserved = json.loads((ROOT / 'docs/visual-evidence/chest-rewards-2026-10-04/preserved-assets.json').read_text())
    asset_changed = [p for p, sha in preserved['hashes'].items() if digest(ROOT / p) != sha]
    assert not asset_changed and len(preserved['hashes']) == 121, asset_changed
    unchanged = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'src', 'visual-game', 'visual-lab/assets', 'Neon_Reliquary_v3.html'], cwd=ROOT).returncode == 0
    assert unchanged
    before = json.loads((OUT / 'dense-fixture.json').read_text())
    after = json.loads((OUT / 'dense-after-switches.json').read_text())
    fields = ['state', 'hero', 'mode', 'difficulty', 'time', 'wave', 'hp', 'level', 'ult', 'ultTime', 'pending', 'kills', 'bosses', 'boss', 'enemies', 'blades', 'warnings', 'position', 'stats', 'damageDealt', 'damageTaken']
    core_changed = [k for k in fields if before['snapshot'].get(k) != after['snapshot'].get(k)]
    core_changed += [k for k in ('skills', 'boss', 'pickups', 'rewards') if before[k] != after[k]]
    assert not core_changed, core_changed
    summary = {
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'cases': len(reports), 'frames': 10080, 'queries': 30240, 'invalidated': 0,
        'units': 'ms; sum is the per-frame sum of independent context queries, not end-to-end frame time',
        'browserSourcesChecked': len(hashes), 'browserSourceChanges': browser_changed,
        'preservedAssets': 121, 'assetChanges': asset_changed, 'productSourceMatchesCommit': unchanged,
        'denseCoreComparison': {'unchangedFields': fields, 'changed': core_changed},
        'probeSources': {p: digest(ROOT / p) for p in ('tools/visual_gpu_probe.js', 'tools/visual_gpu_scenarios.js')},
        'casesMeasured': [{'label': r['label'], 'samples': len(r['rows']), 'gpuMs': r['gpuMs'], 'sumGpuMs': r['totalGpuMs'],
                           'frameIntervalMs': r['frameIntervalMs'], 'raw': r['label'] + '.json'} for r in reports],
    }
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    lines = ['# 逐场景 GPU 实测汇总', '', '方法、覆盖与边界见 [QA.md](QA.md)。所有数值为毫秒；汇总是每帧三个独立上下文查询值之和。', '',
             '| 场景 / 原始记录 | 有效帧 | 原生 P50 / P95 | 场地 P50 / P95 | 高清 P50 / P95 | 汇总 P50 / P95 |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in reports:
        values = [f"{r['gpuMs'][k]['median']:.3f} / {r['gpuMs'][k]['p95']:.3f}" for k in LAYERS]
        total = r['totalGpuMs']
        lines.append(f"| [{r['label']}]({r['label']}.json) | {len(r['rows'])} | " + ' | '.join(values) + f" | {total['median']:.3f} / {total['p95']:.3f} |")
    (OUT / 'MEASUREMENTS.md').write_text('\n'.join(lines) + '\n')
    print(f"PASS: {len(reports)} cases, 10080 frames, 30240 released queries, {len(hashes)} browser sources, 121 preserved assets; frozen core unchanged")


if __name__ == '__main__':
    main()
