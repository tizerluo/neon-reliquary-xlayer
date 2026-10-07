# October competition update

Status: **live at the original [formal entry](https://1-2-231.tapekit.org/)**. Final release `nr-3fda53bf51b0aa1d` was activated on 2026-10-07, block **72621757**, after all 56 immutable files/archive were fully verified. All 57 files were read back after activation; a transient RPC 502 was recovered through read-only verification, without rebroadcasting transactions. Cloudflare serves the unchanged 60 HD assets. OATH was issued at block 72618561 and the formal game now displays its real addresses and official link. The September HTML is preserved at `archive/pre-competition-84f7e7fe34da45a4.html` in the same on-chain container.

The deployed program was built from clean source **`5c5da19ed1510db6cd1e831d05a44e6d9ac5cac9`**. Later commits only close out documentation and public receipts; they do not require another deployment. [hybrid-receipt.json](../deploy/hybrid-receipt.json) records the activation transaction, 57 exact file hashes, 49 backfill receipts, cumulative 285 successful DeWeb transactions and original archive. [oath-receipt.json](../deploy/oath-receipt.json) records fixed-block issuance settings.

The final current DeWeb package is **3,777,975 bytes** (197 full-package writes), excluding the preserved 931,833-byte September archive. The backfill reused `program-ae019f0ef821fa55` and `art-644f06376532bf36`, uploading only the new HTML, its manifest and root launcher. Actual recorded DeWeb Gas for both publications/archiving was **0 OKB**; OATH listing fee, initial buy and issuance Gas were also **0**. These are receipt facts for this run, not a guarantee about future fees. The separately approved budget stop lines were 0.04 OKB for DeWeb and 0.01 OKB for issuance Gas.

The default HD edition integrates the visual, procedural audio and recoverable loading work from visual commit `5d1b6e94ba1e4a967b47314c925b724e4f4ab69d` into the development source. It retains the circuit workshop, X Layer readback, author provenance, local saves and seven WebMCP tools. Existing source records, explicit credits and on-chain publisher evidence are preserved; a publishing account is not treated as proof of original authorship.

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

- DeWeb: root launcher, immutable release HTML/manifests, and separately versioned runtime modules and licenses. The 50 JavaScript modules resolve on the same origin; no executable dependency is loaded from Cloudflare.
- Cloudflare: 60 versioned HD assets, their byte counts and SHA-256 inventory, asset notice and a separately authored OATH icon. Asset URLs are immutable; CORS permits the DeWeb origin. Model bytes are checked before preparation. Image hashes can also be audited against the manifest.
- Vercel: testing only.

`release/release.json` lists exactly the current files to publish. Old local release folders are retained for rollback, but are not part of the current manifest. Upload immutable program files first; verify every file from the registry; activate the tiny root launcher last. Archive the previous root HTML before activation. Address backfill creates a new HTML release while reusing unchanged program modules.

The public repository is a generated allowlisted snapshot:

```sh
python3 tools/export_public.py --destination ../neon-reliquary-public
```

The destination must be clean. The exporter checks secrets, personal information and live private session credentials before modifying it, retains public author/chain evidence, and excludes private handoffs, research, art working files, sessions and deployment credentials. `public-export-manifest.json` identifies exported bytes and their source commit.

## Verification scope

The integrated candidate passed 122 existing tests and legacy gameplay regression. Independent browser checks exercised six heroes, eight bosses, a real encounter with three chip companions, material quotation and chip readback, blocked-model freezing/retry and hash tampering rejection. Five existing loading/UI tests passed after adding null guards to detached portrait callbacks; the public snapshot rebuilt to identical HTML.

The final formal root redirects to the exact release above, renders HD assets, preserves the existing local record, exposes real OATH addresses/reciprocal links and defaults to stage 2. A 390×844 viewport had no horizontal overflow and wrapped both addresses correctly. Chip #1 was verified/imported on the final gateway; a disconnected-wallet quote explicitly showed unknown inventory and a zero-inventory estimate of 0.06212 OKB before Gas, separating material charges and protocol/tapeout fees. No wallet purchase was needed for these checks; final browser warning/error logs were empty.

Desktop Safari played a real encounter on the first formal hybrid release and verified skill use and pause; the final backfill reused its unchanged program modules. A previous Safari window under automation displayed no scene, while a new independent window on the same release passed; the old-window cause remains unknown, so this is not described as a loading-module fix. Physical iPhone and a public player's paid manufacture flow have not been tested. Videos and the original registration were not updated in this 1–9 implementation scope.
