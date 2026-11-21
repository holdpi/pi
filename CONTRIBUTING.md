# Working on HoldPI

Use Node.js 24, npm and Python 3.9 or newer. The Solidity toolchain is pinned in `contracts/package-lock.json`. Python development tooling is pinned in `requirements-dev.txt`.

## Setup and checks

```sh
npm run setup
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
npm run check
```

`npm run check` checks formatting, dependency advisories, Python lint, economic models, compilation, ABI compatibility and the committed review packages. `npm run preview` serves the website locally. `npm run format` formats editable JavaScript and Solidity. Use `python3 -m ruff format scripts src` for Python.

Run the complete contract suite on BNB state. The runner selects the current head minus 64 blocks and prints its hash. Set `PI_FORK_URL` and `PI_FORK_BLOCK` to reproduce a specific historical run through an archive RPC.

```sh
npm run test:contracts
```

The default-policy suite in `contracts/test/shared/contracts.cjs` runs against both `Pi*` and `Hold*` contracts. Add shared invariants there. Configuration-specific behavior belongs in `contracts/test/protocol.test.cjs`. Keep model tables, Solidity policy and browser exports consistent when changing economics.

## Source ownership

Edit `contracts/src/` and `website/` directly. Shared contract behavior lives in `contracts/src/common/`. The fixed and configurable wrappers supply policy values, initialization and OpenFour descriptors. The architecture document explains the boundaries and invariants. [Architecture](audit/ARCHITECTURE.md)

`contracts/vendor/` retains the pinned OpenFour sources and upstream attribution. `assets/original-site/` retains the recovered design baseline. Generated exports live under `website/review/`. Preserve existing file-level license notices and font licenses.

## Refreshing review exports

A complete clean compile and a passing fork run must precede packaging. The exporter checks that the test receipt covers the current contract source, fixtures, configuration, dependency lock and browser policy models.

```sh
npm run compile:clean
npm run test:contracts
npm run package:review
npm run check
```

Review the source diff, generated manifests, bytecode hashes and test receipt together. Both ZIP writers use fixed metadata and sorted paths so repeated exports from the same inputs produce identical bytes. The protocol ZIP includes the contract sources, required models, tests, compiler input and artifacts. The full review ZIP also contains the website and audit documentation.

The GitHub workflow runs source checks and the full fork suite separately. A provider transport failure should be investigated before changing tests or the pinned fork block. Record the replacement block and hash whenever a provider requires a newer snapshot.

## Integration work

The public repository supplies `CoreHarness` for settlement tests. Four.meme supplies the production Core, Registry, signer flow and registered deployment bindings. Track the composed-system acceptance work in the integration review. Contract refactors change deployment bytecode. Review storage compatibility separately before any beacon upgrade. [OpenFour integration](audit/OPENFOUR.md)

The remaining upstream development dependency advisory and pinned overrides are recorded in the dependency review. [Dependency review](audit/DEPENDENCIES.md)
