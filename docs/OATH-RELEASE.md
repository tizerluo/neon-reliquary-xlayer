# Nandverse OATH release status

Status: **preparing**, 2026-10-07. No deployment transaction, token address, vault address or trading receipt has been confirmed. The game shows this state and does not provide a fabricated trading link.

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

Description prepared for the platform:

> Nandverse is a game ecosystem built around shared NAND/LATCH circuit materials on X Layer. Neon Reliquary is its first live game: free expeditions with human, tactical-chip and external AI squad members. OATH is the planned ecosystem token; future games, consumption, staking and revenue-funded batch buyback/burning are roadmap items. Material sales and game business revenue are accounted for separately from launch trading taxes.

The launch package must quote the actual platform listing fee, use the accepted wallet, and verify the signed configuration before any transaction. Historic zero-fee launches do not prove this launch is free. The accepted 0.01 OKB gas reserve is separate from the final DeWeb publication and listing-fee quotes. No first purchase, graduation push or buyback is part of this release.

After a successful receipt, read the token's creator, vault, tax rates, holder/creator split and protection period from X Layer. Only then set `deploy/oath.json` to `launched`, attach the exact addresses, transaction, block and verified trading URL, rebuild the necessary release increment and verify the live entry again. Launch does not activate consumption or staking.

Official workflow: [IGNIX launching a token](https://ignix.bot/docs/launching-a-token), [vault templates](https://ignix.bot/docs/vault-templates), [read-only HTTP API](https://ignix.bot/docs/developers/http-api).
