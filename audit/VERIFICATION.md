# Reproducing the review

## Local checks and compilation

Use Node.js 24 and Python 3. The reviewed build used Node.js 24.16.0, npm 11.13.0, Hardhat 2.29.1 and the checked-in npm lock. Solidity uses `0.8.24+commit.e11b9ed9`, optimizer 200 runs, via IR and the Paris EVM target. OpenZeppelin is locked at 4.9.6.

From the repository root:

```sh
node --test tests/*.test.cjs
python3 scripts/verify-review.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -c 'from pi_bnb_v2 import checks; from check_model import run; print(checks()["status"]); run()'
(cd contracts && npm ci && npm run compile)
```

The JavaScript checks cover fee and reward tables, finite budget conservation, configuration import/validation and the personalized ZIP. The Python economic model exercises 10,000 seeded actions as well as individual policy checks. The earlier Base model is included for comparison. The review verifier checks site dependencies, original design assets, pinned vendor hashes, both ZIPs and the protocol ZIP's individual file receipts.

## Fork suites

Set `BNB_ARCHIVE_RPC` in your shell to a BNB Smart Chain RPC that can serve historical state at block 134700514. Keep provider credentials local.

```sh
(
  cd contracts
  PI_FORK_URL="$BNB_ARCHIVE_RPC" PI_FORK_BLOCK=134700514 npm test
)
```

Use a recent supported block if the provider has pruned this block, and record the block and hash with your results. Hardhat runs both suites locally using ephemeral accounts. The fork uses actual WBNB and PancakeSwap V2. `CoreHarness` supplies the Core-side settlement adapter.

| Check run on 20 November 2026 | Result |
| --- | --- |
| Fresh npm install with the checked-in lock and compile | Compiled 45 Solidity files |
| BNB fork block 134700514, chain ID 56 | 24 fixed PI cases and 10 configurable preset cases passed |
| Frontend economics and configurable builder | 14 cases passed |
| Independent BNB reference model | Policy checks and 10,000 seeded actions passed |
| Deployed website provenance | All 87 source files under `website/` matched the blobs in the Pages revision. Ten live HTTPS paths, including both ZIPs, matched the same bytes. |
| Build artifact parity | The compiled creation hashes and ABIs matched all 10 legacy records. The freshly built bytecode, runtime templates and ABIs matched all 40 archived Solidity artifact records in the protocol ZIP. |

The fork block hash was `0x07c4e967a9eb3b012e4afc97469b3ac7fa4b69aaba2acaff7643c71e4f9bc1bb`. Prior runs are retained in [the fixed PI receipt](../outputs/contract-verification.json) and [the configurable preset receipt](../website/review/protocol/verification.json). They used historical blocks 133771470 and 133933969, respectively. No results are combined across those blocks for the 34-case rerun.

The site comparison used the [GitHub Pages revision](https://github.com/noirchain/holdpi-site/tree/aa558c61233ec750b1710db02d49a0c2372cc515). It also contains directory-route copies, the custom-domain mapping and `.nojekyll`, which are created by the local staging script.

## Review downloads and compiler inputs

- [PI review ZIP](../website/review/holdpi-bnb-review.zip) contains the published fixed-PI review, with the [compiler input](../website/review/compiler-input.json), [component manifest](../website/review/manifest.json) and [download digest](../website/review/download.json).
- [Protocol review ZIP](../website/review/holdpi-protocol-review.zip) contains both sets of Solidity sources, standard compiler input, artifacts, and default configuration. See its [manifest](../website/review/protocol/manifest.json) and [download digest](../website/review/protocol/download.json).
- [Bytecode receipt](bytecode.json) lists SHA-256 fingerprints of the freshly compiled configurable components. The runtime fingerprints cover compiler templates before immutable values are inserted at deployment.
- [Vendor provenance](../contracts/vendor/PROVENANCE.json) records the OpenFour revision `8ca5554df22ad511126d8547c212fa161ecf19ee` and source hashes. The public [upstream revision comparison](https://github.com/four-meme-community/openfour-docs/compare/8ca5554df22ad511126d8547c212fa161ecf19ee...079a45e9c3358c9f357c84f336c7d915c9f0e9fc) at preparation time showed a later change to two unused Royalty vault sources.

To regenerate review exports, use a disposable checkout with a clean compile and run `python3 scripts/protocol/build-package.py` and `python3 scripts/build-review.py`. These commands overwrite generated review files in that checkout and retain the dated verification receipts. The checked-in ZIPs remain the reference for published bytes. `scripts/rebuild-site.py` documents the original recovery transformation. Serve `website/` directly for the current site.

The fork evidence establishes behavior with the supplied settlement harness and external DEX contracts. Four.meme's composed Core/Registry/FeeRouter, signed creation, production registration, keeper operation, final launch bindings and independent review are pending. See [Four.meme integration review](OPENFOUR.md) for the platform acceptance checks.
