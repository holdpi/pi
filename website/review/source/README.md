# HoldPI audit repository

HoldPI is a BNB Smart Chain token design and configurable OpenFour preset. The same acquisition-age model drives the PI reference token, the configurable contracts, and the builder on [holdpi.com](https://holdpi.com). The website is live. The preset is pending Four.meme review and registration, and the project supplies no deployed HoldPI contract addresses.

## Start here

| Review area | Entry point |
| --- | --- |
| Scope, source provenance, and local verification | [Audit scope](audit/SCOPE.md) |
| PI defaults, acquisition accounting, payouts, and the treasury | [Mechanics](audit/MECHANICS.md) and [exact builder defaults](audit/default-configuration.json) |
| Shared implementations and accounting invariants | [Architecture](audit/ARCHITECTURE.md) |
| Four.meme module composition, schemas, authorities, and integration questions | [OpenFour integration](audit/OPENFOUR.md) |
| Pinned tooling and remaining upstream advisories | [Dependency review](audit/DEPENDENCIES.md) |
| Reproducible tests, bytecode comparison, and evidence limits | [Verification](audit/VERIFICATION.md) |
| Solidity, tests, and pinned upstream sources | [Fixed PI](contracts/src), [configurable preset](contracts/src/protocol), [fork tests](contracts/test), [vendor provenance](contracts/vendor/PROVENANCE.json) |
| Website, calculator, builder and source downloads | [Website](website), [browser model tests](tests), [public site deployment](docs/DEPLOYMENT.md) |

## Run locally

Use Node.js 24, npm, and Python 3.9 or newer. From the repository root, install the development dependencies and run the checks.

```sh
npm run setup
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
npm run check
npm run preview
```

If you downloaded the full review ZIP, regenerate its excluded downloadable ZIP files before the aggregate check. After installing dependencies, run `npm run compile:clean`, `npm run test:contracts`, and `npm run package:review`, then `npm run check`. The archive includes the source and receipts needed for this workflow.

The preview listens at `http://127.0.0.1:8188`. Open `/protocol` for the configuration builder, `/docs` for the product documentation, and `/brandbook` for the visual reference. The homepage includes a client-side presentation gate. The builder can export settings and source locally. Its on-chain launch action is disabled.

The Solidity integration suites use a local Hardhat fork of BNB Smart Chain. See [Verification](audit/VERIFICATION.md) for the fork inputs and how to distinguish the harness results from Four.meme platform integration.

Review downloads are generated from the editable source and source-bound test receipts in this repository. The production website revision is recorded separately in the deployment document. Third-party contract source and fonts retain their upstream notices. Contributor commands and export procedures are documented in [CONTRIBUTING.md](CONTRIBUTING.md).
