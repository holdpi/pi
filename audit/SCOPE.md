# Audit scope and provenance

This repository is a standalone snapshot prepared for Four.meme reviewers. It includes the site, the economic models, both Solidity variants, platform-facing helpers, and the receipts needed to trace the review build. The canonical HoldPI source baseline is commit `dda50ec30c4b00ed0e7052558cd0ea09b06b54ba`. The initial public snapshot is commit `c7477c41de536224afebfa63d3a8996a7ea9ccb2`. The current revision consolidates shared implementations, runs behavioral tests across both variants and regenerates review exports from source-bound evidence.

| Layer | Scope |
| --- | --- |
| PI reference | `contracts/src/Pi*.sol` implements the fixed 5% buy and acquisition-age sell schedule, WBNB rewards, treasury and graduation. Start with `PiToken.sol`, `PiRates.sol`, `PiRewards.sol`, and `PiTreasury.sol`. |
| Configurable preset | `contracts/src/protocol/` implements the reusable proposal. Start with `HoldConfig.sol`, `HoldToken.sol`, `HoldRewards.sol`, and `HoldPresetValidator.sol`. It shares the core age rules with fixed PI. |
| Platform composition | `contracts/vendor/` contains the upstream source snapshot consumed at build time. `contracts/src/test/CoreHarness.sol` supplies the local settlement adapter used in tests. `contracts/protocol/` covers local registration, ABI preparation and unsigned simulation. |
| Economic reference | `src/pi-bnb-v2-spec.json`, `src/pi_bnb_v2.py`, and `src/epoch_model.py` model the default mechanics and conservation of funds. `src/base-v1-spec.json` and `src/check_model.py` retain the earlier Base design for provenance. |
| Presentation and configuration | `website/index.html`, `website/economics.js`, `website/docs.html`, and `website/protocol*` cover the public claims, calculator, terms and export UI. `assets/original-site/` carries the recovered design baseline. |
| Testing and packaging | `contracts/test/`, `tests/`, `scripts/verify-review.py`, the review generators in `scripts/`, and the generated review downloads with compiler inputs, ABIs, source and source-bound test evidence. |
| Operations | `docs/KEEPER.md` describes the keeper policy. `docs/DEPLOYMENT.md` maps the static site to its published revision. Production credentials, maintainer-only site operations, and local work logs stay with the owner. |

Editable source is in `contracts/` and `website/` at the repository root. Shared contract implementations live in `contracts/src/common/`. Both ZIPs and the source viewer are generated from this checkout. The builder consumes the protocol ZIP and appends the selected configuration. The original published files remain traceable through Git history and the production deployment revision.

The production site has a static hosting pipeline. The review checkout contains the preview server, browser logic and transaction preparation tools. Keeper operation is a design and an on-chain interface at present. There is no funded keeper service, project indexer, backend for production wallet transactions, or creation-signing service in this project.

Use [Mechanics](MECHANICS.md) to map claims to code, [OpenFour integration](OPENFOUR.md) to review the composed system, and [Verification](VERIFICATION.md) to reproduce the package checks.
