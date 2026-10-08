# October competition update

Status: **live at the original [formal entry](https://1-2-231.tapekit.org/)**. The October 8 visual-fix release `nr-c8d3d50f24562fb8` / `program-47e9718b9f0b9434` was activated at block **72683713** after full verification of all 58 non-root files. All 59 on-chain files were read back after activation and independently matched the frozen inventory; the normal HTTPS root opens this exact release. Cloudflare continues to serve the unchanged 60 HD assets (`art-644f06376532bf36`). OATH's existing issuance and game configuration are retained.

The [October competition video](https://youtu.be/G7RmBifrycg) (2:57.8, English) records October 7 gameplay and readback, with October 8 annotations for this formal release. Its preserved 285-write/57-file narration is dated footage; this release added 199 writes for **484 cumulative successful DeWeb writes**, with 59 release/archival files verified. [Video scope](COMPETITION-VIDEO-2026-10.md) explains the recorded quote and mobile emulation.

The deployed package was exported from clean source **`281368869a1b18b2635d7c243d5661e13c0b42ca`**, with exactly the runtime bytes independently accepted at fix commit `eaca908d39c5f2267ce272b7f44260e04e14ab60`. Later commits close out documentation and receipts. [hybrid-receipt.json](../deploy/hybrid-receipt.json) records all 59 file hashes, 199 new receipts, 484 cumulative successful DeWeb writes, the activation transaction `0x2aced856139469471f681c985b14889a775f9b55f04821687791fcb6754c0df7`, and both historical archives. [oath-receipt.json](../deploy/oath-receipt.json) preserves the existing issuance evidence.

The current 57-file DeWeb package is **3,778,906 bytes** (198 full-package writes). This publication also archived the prior root launcher at `archive/launcher-nr-3fda53bf51b0aa1d-dd16ba701ac1748d.html` and reused the already verified 931,833-byte September archive at `archive/pre-competition-84f7e7fe34da45a4.html`. The exact plan contained 238 calls: 199 new writes and 39 reused archive chunks. The program version contains 51 runtime modules; the CF inventory and 86,701,291 asset bytes are unchanged. Actual Gas for this publication was **0.0 OKB**, cumulative DeWeb Gas **0.0 OKB**, within the continuing 0.04 OKB stop line. The prior OATH listing fee, initial purchase and issuance Gas were 0; no new token action was needed. Receipt costs do not guarantee future fees.

The default HD edition integrates the visual, procedural audio and recoverable loading work from visual commit `5d1b6e94ba1e4a967b47314c925b724e4f4ab69d`. It retains the circuit workshop, X Layer readback, author provenance, local saves and seven WebMCP tools. The October 8 change fixes menu actor reuse after battle and portrait selection captions; it does not alter art, audio, combat values, save rules or economy code. Existing source records, explicit credits and on-chain publisher evidence are preserved; a publishing account is not treated as proof of original authorship.

## Reproduce

```sh
npm ci --ignore-scripts
python3 build.py
npm test
python3 tools/export_static.py
python3 tools/export_hybrid.py --cdn-origin https://nandverse-assets.pages.dev
python3 -m http.server 4186 --bind 127.0.0.1
```

Open `http://127.0.0.1:4186/Neon_Reliquary_v3.html` for local source play, or `/release/deweb/index.html` for the exact nested hybrid candidate. The static export is available at `/dist/index.html`. HD files need HTTP serving; opening the HTML directly uses the native fallback when module loading is unavailable.

## Publication layout

- DeWeb: root launcher, immutable release HTML/manifests, and separately versioned runtime modules and licenses. The 51 JavaScript modules resolve on the same origin; no executable dependency is loaded from Cloudflare.
- Cloudflare: 60 versioned HD assets, their byte counts and SHA-256 inventory, asset notice and a separately authored OATH icon. Asset URLs are immutable; CORS permits the DeWeb origin. Model bytes are checked before preparation. Image hashes can also be audited against the manifest.
- Vercel: testing only.

`release/release.json` lists exactly the current files to publish. Old local release folders are retained for rollback, but are not part of the current manifest. Upload immutable program files first; verify every file from the registry; activate the tiny root launcher last. Archive the previous root HTML before activation. Address backfill creates a new HTML release while reusing unchanged program modules.

The public repository is a generated allowlisted snapshot:

```sh
python3 tools/export_public.py --destination ../neon-reliquary-public
```

The destination must be clean. The exporter checks secrets, personal information and live private session credentials before modifying it, retains public author/chain evidence, and excludes private handoffs, research, art working files, sessions and deployment credentials. `public-export-manifest.json` identifies exported bytes and their source commit.

## Verification scope

The earlier integrated release passed 122 existing tests and legacy gameplay regression, with browser coverage for six heroes, eight bosses, three chip companions, material quotation/readback and recoverable asset loading. Those results retain their original scope.

For the October 8 fixes, 18 directly relevant tests passed. Local Chromium exercised six heroes through real battle → pause → selection → home actions, all eight bosses with bounded cache eviction, a Volt three-chip encounter through 02:30/wave 4, and 36 portrait combinations (six heroes × two languages × three widths). The independent physical iPhone Safari candidate check used the same runtime in a LAN standalone package: Volt returned from 01:17/wave 2 with the hero visible on selection and home, both caption languages were readable, and four bosses could be viewed before returning home.

After activation, independent pinned-block reads verified all 59 registry files and all 199 new receipts. The gateway's ordinary HTTP response is a bootstrap page; its Service Worker serves the on-chain files to the browser. Independent desktop Chromium checks covered normal root navigation to the exact release, HD home/selection, portrait captions and existing local-save preservation. The publishing session completed the remaining formal checks: Volt battle through 02:12/wave 4, return to selection and home, four ready Boss models followed by home, and native macOS Safari battle through 03:57/wave 6 with the same return path. All returned hero views were visible; Chromium readiness and cache metrics passed. These remaining browser checks were performed by the publisher and are not independent acceptance. Independent anonymous HTTPS reads of all 60 CF runtime assets matched every byte count and SHA-256, with CORS and immutable cache headers; the unchanged 67-file inventory was also compared. The public allowlist snapshot is rebuilt and scanned separately.

**Formal-release iPhone Safari recheck is pending.** Candidate phone acceptance and desktop portrait checks do not establish the new formal HTTPS chain on a physical phone. Subjective audio, simultaneous two-finger input, exact FPS/GPU and zero-cache phone startup were outside the candidate check. Its first load briefly displayed preview unavailable before recovering; the cause remains unknown. An existing desktop Safari tab showed insufficient chain nodes; a fresh ordinary root tab loaded the new release and passed the battle return. No gateway protection or Service Worker setting was changed, and perfect cold-start reliability is not established. A public player's paid manufacture flow remains untested.
