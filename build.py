"""Build the offline, standalone HTML. Python standard library only."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
html = (SRC / "shell.html").read_text(encoding="utf-8")
core = (SRC / "core.js").read_text(encoding="utf-8").replace("$('bossPhase').textContent = '第二式 · 狂暴';", "$('bossPhase').textContent = tx('phase2');")
for key, name in [("CSS", "style.css"), ("I18N", "i18n.js"), ("AUDIO", "audio.js"), ("RENDERER", "renderer.js"), ("MODELS", "models.js"), ("INSPECTOR", "inspector.js"), ("COOP", "coop.js"), ("RUNTIME", "runtime.js"), ("CIRCUITS", "circuits.js"), ("OATH_DATA", "oath-data.js"), ("PROVENANCE", "provenance.js"), ("OATH", "oath.js"), ("EXPEDITION", "expedition.js"), ("OATH_UI", "oath-ui.js"), ("XLAYER", "xlayer.js"), ("FORGE_UI", "forge-ui.js")]:
    html = html.replace("__" + key + "__", (SRC / name).read_text(encoding="utf-8"))
html = html.replace("__CORE__", core)
html = html.replace("__OATH_CSS__", (SRC / "oath.css").read_text())
html = html.replace("__RESPONSIVE_CSS__", (SRC / "responsive.css").read_text())
html = html.replace("__ETHERS__", (SRC / "vendor/ethers.umd.min.js").read_text())
output = ROOT / "Neon_Reliquary_v3.html"
output.write_text(html, encoding="utf-8")
print(f"Built {output.name}: {output.stat().st_size:,} bytes")
