# Token mechanics

## Default PI policy

The reference token is Passive Income (PI) with 18 decimals and 1,000,000,000 initial PI. The fixed PI implementation represents one policy. The configurable OpenFour preset initializes each token with its own bounded configuration. Its [default export](default-configuration.json) reproduces the fixed PI tax and weighting tables. Final launch inventory, curve pricing, operations recipient and platform bindings remain open.

| Completed acquisition days | 0 | 1 | 3 | 7 | 14 | 30+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Default sell tax | 10% | 8% | 6% | 4% | 2% | 1% |
| Default holder weight | 0 | 1× | 1× | 1.5× | 1.5× | 2× |

The default buy tax is 5%. Between the listed sell checkpoints, the rate interpolates each cohort day and the reduction rounds down to whole basis points. Age is `max(0, floor(now / 86400) - ceil(receipt / 86400))`. A checkpoint arrives after at least that many full days and less than one additional day. Someone who buys on day 20 and sells within 24 hours faces the same fresh-acquisition rate as someone who bought on launch day. Each top-up starts a new cohort. Exits consume newest acquisitions first and transfers credit the recipient with fresh-age net tokens. Self-transfers and zero transfers leave age and fee balances alone.

## Trade and fee routing

| Path | How the fee is paid |
| --- | --- |
| Bonding buy | Core adds the project fee to the curve quote and routes the quote fee to the treasury. The vault transfers bought PI to the trader and updates curve inventory. |
| Bonding sell | The trade module quotes a whole-basis-point weighted rate for the actual trader and sale amount, rounding up. Core deducts the quote fee on settlement. The recorded-age debit occurs when the bound Core pulls the seller's PI into the vault, with the token fee suppressed for that collection leg. |
| Canonical PancakeSwap V2 buy | The token charges the buy rate on gross token output of the canonical pool to a non-excluded recipient. |
| DEX sell or holder-to-holder transfer | The token debits the sender's newest cohorts, rounds each cohort amount down in token base units, and sends the resulting PI fee to the treasury. |
| Treasury processing | The token and treasury recognize the scoped canonical-pool processing route. Conversion, buybacks and liquidity provision execute separately from user transfers. |

These are project fees. Four.meme fees, gas, anti-sniper where enabled, AMM fees, price impact and conversion costs are separate. Listings, wallets and aggregators need to show the applicable total and quote mixed-age holdings against the correct route.

## Treasury, rewards and claims

During bonding the treasury receives quote fees in WBNB. After migration, `convertTax` converts PI inventory and accounts for actual WBNB receipts. Cumulative floored allocations reserve 70% for holders, 15% for buybacks and burns, 10% for liquidity and 5% for operations at the default mix. For 100 WBNB actually received, the default budgets are 70, 15, 10 and 5 WBNB. Small rounding remainders carry into future allocations. Only the bound operations recipient can withdraw from the operations budget.

A caller can fund the reward ledger from the available holder bucket and settle a round once the interval has elapsed and sufficient funded WBNB and eligible weight exist. The default interval is 900 seconds and the configurable default minimum funding is zero, so a positive pot is still required. Allocation is proportional to the eligible weight measured at settlement. For example, two equal eligible PI balances at 2× and 1× divide a 3 WBNB pot into 2 WBNB and 1 WBNB before integer dust. Multipliers affect the division of the pot. An empty eligible set leaves funding pending. The ledger does not accrue new rewards from elapsed time alone. Already allocated credit survives transfer or sale and can be claimed as WBNB or native BNB, with WBNB fallback for recipients that reject a native payment.

The ledger bounds per-wallet and global cohort work by consolidating fully mature inventory. The auditor should check reserve conservation, delayed settlement, incentives for large holders, observation and keeper liveness, rounding across partial exits, and eligibility through custody or pooling. See [keeper policy](../docs/KEEPER.md).

## Graduation and market controls

The builder default uses 800,000,000 PI for bonding, a 400 WBNB raise, virtual reserves of 1,000,000,000 PI and 100 WBNB, and a 200,000,000 PI reserve for migration inventory. In the no-donation reference scenario, 160,000,000 PI and 400 WBNB seed the pool at the terminal curve ratio. Surplus launch inventory and minted LP go to the dead address. Treasury buyback burns reduce total supply. The same token and reward ledger continue after graduation.

Treasury swaps depend on the canonical PancakeSwap V2 pair, a 30-minute minimum oracle observation period, maximum observation age of two hours, 5% deviation and slippage limits, and a 0.5% reserve batch cap. Buybacks and LP spend their own budgets after graduation. Keeper gas and execution are external inputs. The site calculator illustrates sensitivity to volume, age mix and conversion losses.
