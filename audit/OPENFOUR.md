# Four.meme integration review

HoldPI proposes a custom preset because acquisition-age tax and loyalty require token-level bookkeeping. The configurable preset version in this package is `1.0.0-review`. For module source and encoding, start with [the protocol README](../contracts/protocol/README.md) and [the OpenFour developer guide](https://github.com/four-meme-community/openfour-docs/blob/8ca5554df22ad511126d8547c212fa161ecf19ee/docs/developer-guide.md).

## Composition and parameters

| Slot | Code | Descriptor tag | Init parameters |
| --- | --- | --- | --- |
| Token implementation | `HoldToken` | `token.holdpi_configurable` | Token-module tuple carried in `tokenParams` |
| Token module | `HoldTokenModule` | `module.token.holdpi_configurable` | `HoldConfig.Config` tuple |
| Vault | `HoldVault` | `module.vault.holdpi_bonding` | Empty bytes |
| Curve | `HoldCurveModule` | `module.curve.holdpi_virtual` | `(uint256 virtualToken, uint256 virtualQuote)` |
| Trade | `HoldTradeModule` | `module.trade.holdpi_configurable` | Empty bytes |
| Migration | `HoldMigrateModule` | `module.migrate.holdpi_v2` | Empty bytes |
| Helpers | `HoldRewards` and `HoldTreasury` | Initialized clones | Implementations are bound in the validator and token parameters |
| Validator | `HoldPresetValidator` | Bound per preset by Registry | Constructor binds Core, WBNB, router, helper implementations, and preset ID |

There is no custom data module in the proposed composition. Registry module identifiers and versions are assigned by Four.meme. The local registration helper uses version `1.0.0` and derives keys from the proposed tags. In the Solidity descriptors the short tag ID is the first eight bytes of the tag hash. Use Registry's verified full keys and version snapshots for the formal integration.

The encoded token tuple consists of Core, rewards implementation, treasury implementation, router, operations recipient, `buyBps`, 31 daily `sellBps` entries, 31 daily `weightBps` entries, `roundSeconds`, `minFunding` in wei, and four `splitBps` entries ordered holders, burn, liquidity, operations. Prices, supply and sale amounts are integers in the assets' base units. The [builder default export](default-configuration.json) captures the data as submitted before binding deployment addresses.

The on-chain policy allows buy and sell taxes from 0 to 1,000 bps, a non-increasing sell schedule, and non-decreasing weights starting at zero with a mature weight from 1× to 5×. It requires a round interval from 60 to 86,400 seconds, a funding minimum from 0 to 1,000,000 BNB and splits summing to 10,000 bps. The validator also checks positive supply and LP reserve, WBNB, bound implementations, and compatibility of the curve's raise endpoint and migration inventory. The builder applies its own input constraints before exporting the raw tuples.

The trade module rejects mismatched token contexts, empty trades, and unquotable seller amounts through `TradeNotAllowed`. It proposes a single extra fee tier to the treasury and imposes no configured per-wallet holding limit. Validation failures have `HOLD:` reason strings, including policy shape, cadence, split, trusted components and terminal LP inventory. Certain curve, vault and migration errors retain the baseline prefixes. Use the source and ABIs for exact error decoding.

## Authority and custody

| Actor or component | Authority or dependency |
| --- | --- |
| OpenFour Core, Registry and deployer | Platform-managed preset, beacons, allowed modules, phase changes, token creation, fee routing and settlement. Review the selected deployment and upgrade controls. |
| Authorized Core creation signer | Platform signature binds the request to the creator and chain. The project supplies ABI encoding and read-only validation, with signature and verified registry bindings still required. |
| Bound token module, vault and migration module | Initialize the token, settle bonding trades, and move migration inventory through distinct caller checks. Configurable policy is set on token initialization. |
| Operations recipient | Can withdraw its allocated WBNB operations balance. Other treasury budgets have purpose-specific methods. |
| Keepers and holders | Anyone can call eligible processing functions at their own gas cost. A holder claims that holder's accrued credit. There is no funded keeper in scope. |
| WBNB and PancakeSwap V2 | Quote asset, conversion, price observations, canonical pair and LP lock. Test and approve the actual router/factory bindings. |

## Checks requested from Four.meme

1. Bind the approved BNB-chain deployment, Core/Registry/FeeRouter/Tools and signer versions, module IDs, beacons, roles, and runtime code hashes. Confirm the preset-specific quote asset, supported project-tax cap, fee routing and extra platform fees.
2. Create on a platform-supported fork using the actual module registry and signer flow. Verify schema order, the validator, runtime identities, the policy hash and the `TokenCreated` receipt. Review the official metadata and author fields with the project owner before registration.
3. Verify bonding buy and sell traces. Check who is passed as trader and which account pulls tokens into the vault, the effective size used for the tax quote, and routing to the treasury. The current sell exemption depends on the bound Core's direct collection into the vault while Trading. Review exact-amount, budget, relayed and Permit2 paths wherever the platform supports them. Require parity between quote and receipt with one project tax per trade.
4. Verify phase transitions and migration through the official Core. The migration module returns `(1, abi.encode(canonicalPair))`. Confirm that the production pool-kind decoder, state update and indexer resolve the intended PancakeSwap V2 pair, terminal inventory, preserved reward balances and LP sent to the dead address. Restrict routing claims to combinations verified with fee-on-transfer tokens.
5. Review reward backing, rounding, timestamp boundaries, tick and keeper liveness, maximal cohort gas, delayed settlement incentives and the effect of noncanonical pools or custodial holdings. Independently verify the treasury oracle, inventory limits, and segregation of spending and claims.
6. Confirm whether any HoldPI configuration or claim workflow needs a dedicated page in OpenFour. The included HoldPI builder is a review reference. If Four.meme requires extra preset pages, agree on the official fork demo and style-pack submission format before admission.

For indexing, correlate Core creation/trade/migration receipts and the canonical pair with the token's `BondingTaxNotified` and ERC-20 `Transfer` events. Account for WBNB with treasury `Allocated`, `Converted`, `BuybackBurn`, `LiquidityAdded` and `OracleObserved` events, and reward `Funded`, `Distributed` and `Claimed` events. A quote notification alone does not establish a funded balance.

The review fixtures exercise real WBNB and PancakeSwap V2 through a local settlement harness. The official Core composition, independent security review, registered preset and deployable launch bindings remain pending.
