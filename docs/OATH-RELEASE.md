# Nandverse OATH release status

Status: **issued on X Layer**, 2026-10-07, block **72618561**. The original publisher wallet created the token with listing fee 0 and initial buy 0. Actual recorded issuance Gas was **0 OKB**.

- Token: `0x66e59AB78F32cdA17a69E3784B0B67E17b76eeEE` ([official trading page](https://ignix.bot/launch?token=0x66e59ab78f32cda17a69e3784b0b67e17b76eeee)).
- System Vault: `0x6fDD99885b32146FB7bA388E2dc4aC3e9dfDAa65`.
- Dividend tracker: `0x7DcF8a05e89888621C757971BABC049d14cA74F5`.
- [Confirmed creation transaction](https://www.oklink.com/x-layer/tx/0x95271e9cafc580b023183afc52db762c11db5f20b1465b13714a385aa80702fd).
- Public fixed-block readback: [oath-receipt.json](../deploy/oath-receipt.json).

| Parameter | Accepted setting |
|---|---|
| Chain | X Layer, 196 |
| Name / ticker | Nandverse OATH / OATH |
| Launch / quote | IGNIX Standard / native OKB |
| Vault | System Vault |
| Buy / sell tax | 1% / 1% |
| Tax allocation | Holders 20%, project 80% |
| Issuer and project receiver | Original publisher `0xb5c09b3322e21d459570c9c882d56f5b0769559e` |
| Initial buy | 0 |
| Holder dividend threshold | 0 OATH (no minimum) |
| Dividend asset | Quote token (OKB) |
| Anti-snipe | Disabled |
| Tax token graduation protection | 1 day |
| Website | https://1-2-231.tapekit.org/ |
| Icon | https://nandverse-assets.pages.dev/tokens/oath/icon-v1.png |

Published platform description:

> Nandverse is a game ecosystem built around shared NAND/LATCH circuit materials on X Layer. Neon Reliquary is its first live game: free expeditions with human, tactical-chip and external AI squad members. OATH is the ecosystem token; future games, consumption, staking and revenue-funded batch buyback/burning are roadmap items. Material sales and game business revenue are accounted for separately from launch trading taxes.

The platform returned listingFee=0 for this launch, and the confirmed zero-value transaction used the original wallet. No first purchase, graduation push or buyback was performed. The accepted 0.01 OKB issuance Gas reserve and 0.04 OKB DeWeb publication/backfill budget are separate; both are budget stop lines rather than guarantees about future fees.

The creation receipt and fixed-block getters confirmed the original creator, native quote, Vault/tracker, 100/100 BPS tax, 2000/8000 BPS split, minimum holding 0, anti-snipe 0/0 and protection duration 86400 seconds. The same complete Vault data was exercised on an isolated local fork: native tax split 20/80 and creator claim recipient were verified. `deploy/oath.json` now records the real addresses, receipt and official trading URL; the game defaults to stage 2. Launch does not activate consumption or staking.

Official workflow: [IGNIX launching a token](https://ignix.bot/docs/launching-a-token), [vault templates](https://ignix.bot/docs/vault-templates), [read-only HTTP API](https://ignix.bot/docs/developers/http-api).
