# Reproducing the review

## Toolchain and local checks

Use Node.js 24, npm and Python 3.9 or newer. This revision uses Hardhat 2.29.2, Solidity `0.8.24+commit.e11b9ed9.Emscripten.clang`, optimizer 200 runs, via IR and the Paris EVM target. OpenZeppelin is pinned at 4.9.6. Dependency advisories and the targeted development-tool overrides are recorded separately. [Dependency review](DEPENDENCIES.md)

```sh
npm run setup
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
npm run check
```

The aggregate command checks formatting, dependency advisories, Python lint, both economic models, compilation, public ABI compatibility and review artifact consistency. The browser model suite contains 14 cases. The Python models include policy checks and 10,000 seeded actions. GitHub Actions also runs the complete fork suite in a separate job.

## Contract execution

```sh
npm run test:contracts
```

The runner defaults to a public BNB RPC and selects the head minus 64 blocks. It prints the block number and hash before running. Set `PI_FORK_URL` and `PI_FORK_BLOCK` to reproduce a historical snapshot through an archive-capable provider. Keep credential-bearing RPC URLs in your environment.

The committed run at block `134877632` on chain `56` passed all 80 cases. Its block hash is `0x316231b990dec34bc6e05804213cdf129bbf0570e39e165c55e35b56252598f0`.

| Coverage | Cases |
| --- | ---: |
| Public ABI compatibility across the original components | 20 |
| Shared fixed-policy behavior against PI | 25 |
| The same shared behavior against configurable HoldPI | 25 |
| Configurable policy, encoding and validation | 10 |

The fork uses actual WBNB and PancakeSwap V2 contracts. `CoreHarness` supplies the local settlement adapter. The report includes each test result, selected gas measurements, the compiler, fork identity and hashes of the complete current source, test fixtures, dependency configuration and browser policy models. [Executed receipt](../outputs/contract-verification.json)

The ABI regression baseline comes from initial public commit `c7477c41de536224afebfa63d3a8996a7ea9ccb2`. Tests compare callable signatures, return types, mutability, errors and event indexing. Shared implementations change bytecode and internal storage layout. Use this revision for fresh deployments, with a separate storage-compatibility review for any upgrade.

## Generated review packages

```sh
npm run compile:clean
npm run test:contracts
npm run package:review
npm run check
```

Packaging requires a complete compiler input matching every editable Solidity source and a passing, source-bound receipt covering all four suites. A changed contract, fixture, policy model or dependency lock requires a new test run. Both ZIP writers normalize ordering, timestamps and permissions. Repeating the export with identical inputs produces identical ZIP bytes.

- The fixed PI review ZIP contains the website, models, Solidity, tests, source viewer and audit documentation. [Full package](../website/review/holdpi-bnb-review.zip)
- The configurable protocol ZIP contains the Solidity sources, test dependencies, standard compiler input, artifacts and default configuration. The builder appends the selected configuration to this archive. [Protocol package](../website/review/holdpi-protocol-review.zip)
- The bytecode receipt covers all 20 fixed and configurable components. The verifier compares source hashes and compiled creation and runtime-template fingerprints. Runtime templates precede immutable substitution at deployment. [Bytecode receipt](bytecode.json)
- OpenFour source remains pinned to revision `8ca5554df22ad511126d8547c212fa161ecf19ee`, with individual file digests and upstream notices. [Vendor provenance](../contracts/vendor/PROVENANCE.json)

The initial website publication and original audit snapshot remain traceable through Git history. Current exports represent this checkout. The deployed site revision is recorded in the deployment document. [Website deployment](../docs/DEPLOYMENT.md)

Four.meme's composed Core, Registry, FeeRouter, signed creation, production registration, keeper operation, final launch bindings and independent review remain integration work. [Platform acceptance checks](OPENFOUR.md)
