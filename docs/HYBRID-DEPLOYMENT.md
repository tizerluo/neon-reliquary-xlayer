# October competition update

Status: candidate prepared on 2026-10-07; the original DeWeb edition remains live until upload readback and activation finish. OATH has not been issued.

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

The integrated candidate passed 122 existing tests and legacy gameplay regression. Independent browser checks exercised six heroes, eight bosses, a real encounter with three chip companions, material quotation and chip readback, blocked-model freezing/retry and hash tampering rejection. Desktop Safari played a real encounter and verified skill use and pause. Final DeWeb/CDN-origin checks remain until publication. Physical iPhone has not been tested.
