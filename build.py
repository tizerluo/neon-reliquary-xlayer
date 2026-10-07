"""Build the offline, standalone HTML. Python standard library only."""
from pathlib import Path
import re
import json
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
html = (SRC / "shell.html").read_text(encoding="utf-8")
release = json.loads((ROOT / 'deploy/oath.json').read_text())
if release['status'] == 'launched':
    for key in ('address', 'vault', 'transactionHash', 'tradeUrl', 'blockNumber'):
        if not release.get(key):
            raise ValueError(f'Launched OATH requires verified {key}')
economy = (SRC / 'economy-ui.js').read_text().replace('__OATH_RELEASE_JSON__', json.dumps(release, ensure_ascii=False))
html = html.replace('__ASSET_CONFIG__', (SRC / 'asset-config.js').read_text())
html = html.replace('__ECONOMY_CSS__', (SRC / 'economy.css').read_text())
html = html.replace('__ECONOMY_UI__', economy)
core = (SRC / "core.js").read_text(encoding="utf-8").replace("$('bossPhase').textContent = '第二式 · 狂暴';", "$('bossPhase').textContent = tx('phase2');")
# 音频按依赖顺序拼接：DSP → 音效配方 → 配乐 → 引擎
html = html.replace("__AUDIO__", "\n".join((SRC / name).read_text(encoding="utf-8") for name in ("audio-dsp.js", "audio-sfx.js", "audio-music.js", "audio.js")))
for key, name in [("CSS", "style.css"), ("LOADING_CSS", "loading.css"), ("LOADING_UI", "loading-ui.js"), ("I18N", "i18n.js"), ("UI_BOUNDS", "ui-bounds.js"), ("RENDERER", "renderer.js"), ("MODELS", "models.js"), ("INSPECTOR", "inspector.js"), ("COOP", "coop.js"), ("RUNTIME", "runtime.js"), ("CIRCUITS", "circuits.js"), ("OATH_DATA", "oath-data.js"), ("PROVENANCE", "provenance.js"), ("OATH", "oath.js"), ("EXPEDITION", "expedition.js"), ("OATH_UI", "oath-ui.js"), ("XLAYER", "xlayer.js"), ("FORGE_UI", "forge-ui.js")]:
    html = html.replace("__" + key + "__", (SRC / name).read_text(encoding="utf-8"))
html = html.replace("__CORE__", core)
html = html.replace("__WARNING_DATA__", (SRC / "warning-data.js").read_text(encoding="utf-8"))
html = html.replace("__OATH_CSS__", (SRC / "oath.css").read_text())
html = html.replace("__RESPONSIVE_CSS__", (SRC / "responsive.css").read_text())
html = html.replace("__ETHERS__", (SRC / "vendor/ethers.umd.min.js").read_text())
output = ROOT / "Neon_Reliquary_v3.html"
output.write_text(html, encoding="utf-8")
print(f"Built {output.name}: {output.stat().st_size:,} bytes")
