# Dependency review

The contract toolchain uses pinned versions and a committed npm lock. Hardhat loads the ethers and Chai plugins used by the tests. The unused toolbox, deployment plugins, coverage stack and gas reporter have been removed.

The 21 November 2026 dependency scan reports zero critical, high or moderate advisories. The production dependency set contains the two pinned OpenZeppelin 4.9.6 packages and reports zero npm advisories. The development tree contains 14 low-severity package findings derived from one upstream Elliptic advisory. The lock records the complete dependency graph.

## Remaining upstream issue

`elliptic@6.6.1` is pulled in through Hardhat 2's ethers-v5 ABI dependencies and the network helpers' Ethereum utilities. The reviewed advisory describes incorrect ECDSA signatures for certain intermediate values and possible key disclosure when faulty and correct signatures can be compared. It lists no patched release. This repository uses ephemeral fork accounts for its contract tests. The transaction-preparation helper produces unsigned payloads, and local registration uses the local unlocked signer. [Upstream advisory](https://github.com/advisories/GHSA-848j-6mx2-7j84)

Retain this finding in future toolchain reviews. Removing it requires replacing the affected upstream dependency paths. The CI audit gate rejects moderate-or-higher advisories and reports the remaining low-severity findings.

## Targeted overrides

| Package | Pinned version | Reason |
| --- | --- | --- |
| `tmp` | 0.2.7 | Temporary-path traversal fixes for compiler tooling |
| `serialize-javascript` | 7.1.3 | Serialization and script-escaping fixes used by Mocha |
| `cookie` | 0.7.2 | Cookie validation fix in the legacy diagnostics dependency |
| `diff` | 8.0.3 | Bounded patch parsing in the test reporter dependency |
| `glob` | 14.0.6 | Cancellation handling in test discovery |
| `minimatch` | 11.0.9 | Pattern-amplification fixes in file matching |

Node.js 24 satisfies the overridden packages' engine requirements. The complete compile, ABI compatibility and fork suites exercise the resulting dependency graph. Keep each override under review when updating its parent dependency.

```sh
npm --prefix contracts audit
npm --prefix contracts audit --omit=dev
```
