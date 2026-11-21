"""Rebuild the BNB frontend from the untouched recovered deployed source."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "assets/original-site"
WEB = ROOT / "website"
h = (ORIGINAL / "index.html").read_text()


def replace(old, new):
    global h
    assert old in h, old[:100]
    h = h.replace(old, new)


replace("<title>π — Passive Income</title>", "<title>π - Passive Income on BNB Chain</title>")
replace(
    "The longer you hold, the more you earn. Early sellers pay more, long-term holders pay less.",
    "Purchase-specific tax decay and funded BNB rewards. Early sellers pay more, long-term holders pay less.",
)
replace('<span class="sb-net">MAINNET</span>', '<span class="sb-net">BNB · PRE-LAUNCH</span>')
replace(
    '<a href="#roadmap" class="nav-item">(05) ROADMAP</a>',
    '<a href="#roadmap" class="nav-item">(05) ROADMAP</a>\n        <a href="/docs" class="nav-item">(08) DOCS</a>',
)
replace('href="#" class="cta-mini">BUY $π', 'href="#buy" class="cta-mini">GET $π')
replace('href="#" class="btn btn-pri">BUY $π', 'href="#buy" class="btn btn-pri">GET $π')
replace(
    '<a href="#" class="btn">READ THE SPEC</a>', '<a href="/docs" class="btn">READ THE SPEC</a>'
)
replace("// T-MINUS · NEXT_DISTRIBUTION", "// TARGET · SETTLEMENT_WINDOW")
replace("EVERY 1H · ALL HOLDERS", "15M TARGET · AFTER LAUNCH")
replace(
    "$π is a time-weighted redistribution system. Every trade pays the holders.\n          The longer you hold, the more you earn — early sellers pay more, long-term holders pay less.",
    "$π rewards patience on BNB Chain. Every purchase starts its own clock.\n          Early exits pay more. Longer-held PI receives a larger share of funded BNB rewards.",
)
replace("CONTRACT_ADDRESS · SOL", "CONTRACT_ADDRESS · BNB")
replace("0x0000000000000000000000000000000000000000", "NOT_DEPLOYED")
h = h.replace('data-copy="NOT_DEPLOYED"', 'disabled aria-label="Contract not deployed"')
replace(
    "// placeholder · live address posted at launch",
    "// source available · official address posted after deployment",
)
replace('<span class="led led-sm"></span> LIVE', '<span class="led led-sm"></span> BNB')
replace(
    "Someone buys or sells $π. Every transaction pays a <strong>7% tax</strong> — split <strong>85% to holders</strong>, <strong>15% to liquidity</strong>.",
    "Buy tax is <strong>5%</strong>. Sell tax starts at <strong>10%</strong> for every purchase and decreases toward <strong>1%</strong> over a month.",
)
replace(
    "85% of every tax flows into one shared <strong>redistribution pool</strong>. The more trading, the bigger the pool.",
    "<strong>70%</strong> of collected tax funds BNB rewards. <strong>15%</strong> buys and burns PI, <strong>10%</strong> funds liquidity and <strong>5%</strong> covers operations.",
)
replace(
    "Every <strong>hour</strong> the pool airdrops to all holders, weighted by <strong>balance × time-held multiplier</strong>. No buttons to press.",
    "Funded rounds target <strong>15 minutes</strong>. Eligible holders earn by <strong>balance × holding weight</strong>. Claim accrued BNB when you choose.",
)
# Preserve the original four-quadrant illustration and use the current weights.
for old, new in [
    ("0d · ×1.0", "0d · ×0"),
    ("1d · ×1.5", "1d · ×1"),
    ("7d · ×2.2", "7d · ×1.5"),
    ("30d+ · ×2.5", "30d+ · ×2"),
]:
    h = h.replace(old, new)
h = (
    h.replace(">×1.0</span></div>", ">×0</span></div>")
    .replace(">×1.5</span></div>", ">×1</span></div>")
    .replace(">×2.2</span></div>", ">×1.5</span></div>")
    .replace("×2.5", "×2")
)
replace(
    "// rewards driven by activity, amplified by patience. cap: ×2",
    "// complete holding days: 1x at day 1 · 1.5x at day 7 · 2x at day 30",
)
replace('aria-label="live stats"', 'aria-label="Token parameters and launch status"')
replace('<span class="cell-value">7%</span>', '<span class="cell-value">5%</span>')
replace('<span class="cell-value">3–10%</span>', '<span class="cell-value">1-10%</span>')
for key, old, new in [
    ("strip-holders", "3,142", "PENDING"),
    ("strip-vol", "$487,210", "PENDING"),
    ("strip-pool", "1,247.84 π", "0 BNB"),
]:
    replace(f'id="{key}">{old}', f'id="{key}">{new}')
replace("NEXT_DISTRIBUTION</span>", "ROUND_TARGET</span>")
replace("// LIVE_DATA · NEXT_UP", "// PRE_LAUNCH · NEXT_UP")
replace(
    "Every buy and sell is taxed at <strong>7%</strong>. The fee splits two ways: <strong>85%</strong> to holders, <strong>15%</strong> to liquidity / market support.",
    "<strong>5% on buys.</strong> <strong>10% to 1% on exits.</strong> Collected proceeds split 70% holders, 15% buybacks/burns, 10% liquidity and 5% operations.",
)
replace(">7% TAX</text>", ">5% / 10→1%</text>")
replace(">85%</text>", ">70%</text>")
replace(">15%</text>", ">30%</text>")
replace(">→ LIQUIDITY</text>", ">→ 15 / 10 / 5</text>")
replace('x="22" y="132" width="116" height="74"', 'x="22" y="144" width="116" height="62"')
replace('x="222" y="195" width="116" height="11"', 'x="222" y="179" width="116" height="27"')
replace(
    "Tax accumulates in a pool. Every 1h it airdrops to holders by <strong>balance × time-multiplier</strong>. Multiplier resets on buy. Hard cap: ×2.",
    "BNB rewards divide a finite pot by <strong>eligible balance × holding weight</strong>. Top-ups start fresh without resetting older PI. Maximum weight: ×2.",
)
replace(
    "Selling early is penalized. Patience reduces your exit cost. Tax decays smoothly: <strong>3% + 7% · e<sup>−t</sup></strong> (t in days).",
    "Every purchase begins at <strong>10%</strong>, whatever the launch date. Daily reductions pass <strong>8%, 6%, 4%, 2%</strong> and reach <strong>1%</strong> after 30 complete holding days.",
)
# Retain the oscilloscope style and draw the actual daily fee schedule.
start = h.index("              <!-- y-axis tick labels")
end = h.index("            </svg>", start)
knots = [(0, 1000), (1, 800), (3, 600), (7, 400), (14, 200), (30, 100)]


def bps(d):
    for (a, hi), (b, lo) in zip(knots, knots[1:]):
        if d < b:
            return hi - (hi - lo) * (d - a) // (b - a)
    return 100


points = [(50 + 9 * d, 34 + (1000 - bps(d)) * 161 / 900) for d in range(31)]
curve = f"M {points[0][0]} {points[0][1]:.2f}" + "".join(f" H {x} V {y:.2f}" for x, y in points[1:])
svg = ""
for value in (10, 7, 4, 1):
    y = 34 + (10 - value) * 161 / 9
    svg += f'<text x="22" y="{y + 4:.2f}" class="g-num g-r">{value}%</text><line x1="34" y1="{y:.2f}" x2="346" y2="{y:.2f}" class="g-grid"/>\n'
svg += '<line x1="34" y1="30" x2="34" y2="200" class="g-axis"/><line x1="34" y1="200" x2="346" y2="200" class="g-axis"/>\n'
svg += f'<path class="g-area anim-fade stagger-3" d="{curve} L 320 200 L 50 200 Z"/><path class="g-curve anim-draw" d="{curve}"/>\n'
for d in (0, 7, 14, 30):
    x, y = points[d]
    svg += f'<circle cx="{x}" cy="{y:.2f}" r="3.5" class="g-dot pulse-dot anim-fade stagger-2"/><text x="{x}" y="{y - 12:.2f}" class="g-num g-c anim-fade stagger-2" style="font-size:13px">{bps(d) / 100:g}%</text><text x="{x}" y="222" class="g-lbl g-c">{d}d</text>\n'
h = h[:start] + svg + h[end:]
replace(
    "<strong>15%</strong> of every tax funds the liquidity engine: depth, slippage smoothing, basic market-making logic.",
    "<strong>15%</strong> buys and burns PI. <strong>10%</strong> adds permanently locked liquidity. These budgets accumulate during bonding and execute after graduation.",
)
replace("// ORDER_BOOK · ±2%", "// MARKET_SUPPORT · BUDGETED")
replace(
    'PROJECT <span class="hl hl-lime">YOUR</span> YIELD',
    'MODEL <span class="hl hl-lime">YOUR</span> SHARE',
)
replace(
    "// time × share. type your numbers, see the math.",
    "// finite BNB pool × normalized weight. change the assumptions, see the math.",
)
replace('value="500000" min="0" step="10000"', 'value="100" min="0" step="10"')
replace(
    '<span class="calc-unit calc-unit-l">$</span>', '<span class="calc-unit calc-unit-l">BNB</span>'
)
for d, m in [(0, 0), (1, 1), (3, 1), (7, 1.5), (30, 2)]:
    h = re.sub(r'(data-days="' + str(d) + r'"\s+data-mult=")[^"]+', lambda x: x[1] + str(m), h)
extra = ""
for label, id, value, step, unit, maxi in [
    ("BUY_VOLUME", "calc-buys", 50, 5, "%", 100),
    ("AVG_SELL_TAX", "calc-average-sell", 4, 0.1, "%", 10),
    ("OTHER_WEIGHT", "calc-other-weight", 500000000, 1000000, "PI × w", ""),
    ("CONVERSION_COST", "calc-conversion", 0.5, 0.1, "%", 100),
]:
    extra += (
        f'<label class="calc-row"><span class="calc-lbl">{label}</span><span class="calc-input-wrap"><input aria-label="{label}" type="number" id="{id}" value="{value}" min="{1 if id == "calc-average-sell" else 0}" '
        + (f'max="{maxi}" ' if maxi != "" else "")
        + f'step="{step}"/><span class="calc-unit">{unit}</span></span></label>\n'
    )
replace(
    '<div class="calc-meta">// values are illustrative · payouts are airdropped in SOL</div>',
    extra
    + '<div class="calc-meta">// BNB scenarios, not a live yield quote. OTHER_WEIGHT excludes your PI. Days are completed cohort days; thresholds can take less than one extra day. Low volume may defer a round.</div>',
)
replace('placeholder="paste SOL address…"', 'placeholder="Available after deployment" disabled')
replace(
    'id="calc-lookup" class="lookup-btn">[ SCAN ]',
    'id="calc-lookup" class="lookup-btn" disabled>[ PENDING ]',
)
replace("// PROJECTED_YIELD", "// BNB_REWARD_SHARE")
replace('data-cycle="1h">1H', 'data-cycle="15m">15M')
replace(">NEXT_DROP_SHARE<", ">ELIGIBLE_SHARE<")
replace(">WEEKLY<", ">BUYBACK / DAY<")
replace(">MONTHLY<", ">LIQUIDITY / DAY<")
replace(">ANNUALIZED<", ">OPERATIONS / DAY<")
replace(
    "// from zero to first π in under five minutes.",
    "// prepare for launch. trading links activate after deployment.",
)
replace(
    "Install Phantom (or any Solana-compatible wallet). Browser extension or mobile app — both work.",
    "Use a wallet that supports BNB Smart Chain. Select the BNB network and keep enough BNB for transaction fees.",
)
replace("https://phantom.app", "https://trustwallet.com")
replace("→ phantom.app", "→ trustwallet.com")
replace("FUND IT WITH SOL", "FUND IT WITH BNB")
replace(
    "Buy SOL on any major exchange (Coinbase, Binance, Kraken) and send it to your new wallet.",
    "Send BNB to your wallet on BNB Smart Chain. Check the network and receiving address before transferring.",
)
replace(
    "Open Jupiter or Raydium, paste the contract address from above, swap SOL for $π. You're in.",
    "At launch, use the verified Four.meme page. After graduation, use the official PancakeSwap pool. Check the displayed buy and sell fees.",
)
replace(
    '<a href="#" class="step-link">→ swap on jupiter</a>',
    '<a href="/docs#launch" class="step-link">→ launch specification</a>',
)
replace(
    "Initial token contract written. Tax + redistribution logic finalized.",
    "Solidity review package: acquisition-age ledger, taxes, BNB rewards, treasury and OpenFour modules. Source and local test results are in the documentation.",
)
replace("[ IN_PROGRESS ]", "[ REVIEW_REQUIRED ]")
replace(
    "Independent third-party review of redistribution + tax-decay mechanics. Report published openly.",
    "Independent security audit and OpenFour integration review are required before deployment. Local tests are available; no external audit is claimed.",
)
replace(
    "Public token launch on Solana. No team allocation. No presale. Liquidity locked at deploy.",
    "Proposed BNB launch through a custom OpenFour preset. Supply enters sale and liquidity inventory. Admission and final launch parameters remain to be approved.",
)
replace("[ Q3 ]", "[ AFTER_GRADUATION ]")
replace("[ Q4 ]", "[ LATER ]")
replace(
    "Jupiter, Raydium, Birdeye. Liquidity locked indefinitely. Live pools.",
    "PancakeSwap V2 graduation with LP sent to the burn address. Purchase ages and previously earned BNB survive migration.",
)
replace(
    "Application to mid-tier centralized exchanges. Wider distribution. Increased volume → more redistribution.",
    "Additional venues only after compatibility review. Custodial and pooled balances cannot represent each underlying user on-chain.",
)
questions = [
    (
        "What is the contract address?",
        "PI is not deployed. The verified BNB address and official trading links will be published here after review and deployment. The downloadable source is available now.",
    ),
    (
        "How often are rewards allocated?",
        "The target is one funded settlement every 15 minutes. A keeper submits the transaction when processing is economical; low activity may defer it. Eligible holders accrue a share of the actual BNB pool and claim when they choose. No fixed payout is promised.",
    ),
    (
        "How are taxes split?",
        "Buys pay 5%. Exits pay 10% down to 1%, based on the age of the PI sold. Of the project tax actually collected: 70% funds BNB rewards, 15% buys and burns PI, 10% funds liquidity and 5% covers operations. Platform and swap fees are separate.",
    ),
    (
        "Does the launch date change my sell tax?",
        "No. Every purchase starts at 10%, even months after launch. Checkpoints are 10%, 8%, 6%, 4%, 2% and 1% at completed holding days 0, 1, 3, 7, 14 and 30. Rates decrease daily. Conservative daily buckets can delay a checkpoint by less than one day.",
    ),
    (
        "Does buying more reset my older PI?",
        "No. A new purchase gets a new age bucket. Older PI keeps its age. Sales consume the newest PI first, so fresh funds cannot inherit the lower tax of an old wallet. Wallet transfers pay the applicable exit tax and start a fresh clock for the recipient.",
    ),
    (
        "How does holding time affect rewards?",
        "New PI qualifies after one complete holding day. Eligible weights are 1x before day 7, 1.5x from day 7 and 2x from day 30. Your weight is divided by all eligible weight. If everyone has 2x, nobody receives twice the pool.",
    ),
    (
        "Is the contract audited?",
        "No independent audit has been completed. The documentation contains review source, build instructions, executed local tests and the remaining integration checks. This site does not present local verification as external approval.",
    ),
    (
        "What happens if trading volume stops?",
        "No new fee receipts means no new reward income. Existing credited BNB remains claimable. Empty-eligibility rounds retain the full holder reserve for a later allocation.",
    ),
    (
        "What is the supply and team allocation?",
        "The reference configuration keeps the original one-billion PI supply. All initial inventory goes to the launch vault for sale and liquidity, with no team mint. Operations receives 5% of collected taxes. Final sale and liquidity quantities must be validated before launch.",
    ),
]
faq = "\n".join(
    '<li class="faq-item"><details><summary><span class="faq-q">'
    + q
    + '</span><span class="faq-toggle" aria-hidden="true">+</span></summary><div class="faq-a">'
    + a
    + "</div></details></li>"
    for q, a in questions
)
h = re.sub(r'(<ul class="faq-list">).*?(</ul>)', lambda m: m[1] + faq + m[2], h, flags=re.S)
replace(
    "A volume-driven redistribution game (7% tax · 85/15 split).",
    "A fee-funded BNB redistribution system with a 70/15/10/5 allocation.",
)
replace(
    "A time-weighted multiplier on top — patience amplifies your share, capped at ×2.",
    "A normalized holding weight: patience increases your share, capped at ×2.",
)
replace("SOL · MAINNET", "BNB · PRE-LAUNCH")
replace("// CONTRACT · SOL", "// CONTRACT · BNB")
replace(
    'href="#" class="footer-link">→ GitHub', 'href="/docs#source" class="footer-link">→ Source code'
)
for social in ["Twitter / X", "Telegram", "Discord"]:
    replace(
        f'<a href="#" class="footer-link">→ {social}</a>',
        f'<span class="footer-link">→ {social} · pending</span>',
    )
replace(
    "[ BRAND_BOOK → ]</a>",
    '[ BRAND_BOOK → ]</a> <a class="footer-bar-link" href="/docs">[ DOCUMENTATION → ]</a>',
)
replace("FAIR_LAUNCH · NO_TEAM_ALLOC", "BNB · REVIEW_SOURCE")
replace(
    '<script src="script.js"></script>',
    '<script src="economics.js"></script>\n  <script src="script.js"></script>',
)
h = h.replace("—", "-").replace("–", "-")
(WEB / "index.html").write_text(h)

js = (ORIGINAL / "script.js").read_text()
a = js.index("// ---------- live ticking values")
b = js.index("// ---------- scroll progress", a)
js = (
    js[:a]
    + "// Pre-launch statistics remain pending until a verified on-chain feed is configured.\n\n"
    + js[b:]
)
a = js.index("// ---------- yield calculator")
b = js.index("// ---------- scroll-in entrance", a)
js = js[:a] + (ROOT / "scripts/calculator-ui.js").read_text() + "\n\n" + js[b:]
js = js.replace("const dropInterval = 1 * 3600;", "const dropInterval = 15 * 60;")
js = js.replace(
    "if (text.includes('–')) return true;", "if (/^\\d+-\\d+%$/.test(text)) return true;"
)
js = js.replace("// SYS · MAINNET", "// SYS · BNB · REVIEW")
js = (
    js.replace("7% tax · 85% to holders · 15% to LP", "5% buy · 10→1% sell · 70/15/10/5 allocation")
    .replace("multiplier = 1 + 1.5·t/(t+2)   cap ×2.5", "holding weight = 0 / 1 / 1.5 / 2")
    .replace(
        "sell_tax  = 3% + 7%·e^(-t)     floor 3%", "sell tax follows each acquisition; floor 1%"
    )
)
# The original locks the title at height zero while hidden behind its gate.
# Start the identical effects only once the page is visible and fonts are ready.
js = (
    "(() => { let started=false; const start=async()=>{if(started)return;started=true;await document.fonts.ready; const intro=document.querySelector('.tv-on'); if(intro) intro.replaceWith(intro.cloneNode(true));\n"
    + js
    + "\n}; if(document.documentElement.classList.contains('is-unlocked')) start(); else window.addEventListener('pi:unlocked',start,{once:true}); })();\n"
)
(WEB / "script.js").write_text(js)
gate = (
    (ORIGINAL / "gate.js")
    .read_text()
    .replace("SOL · MAINNET", "BNB · PRE-LAUNCH")
    .replace("BNB · PRE-LAUNCH · PRE-LAUNCH", "BNB · REVIEW_BUILD · PRE-LAUNCH")
)
gate = gate.replace(
    "gate.remove();", "gate.remove();\n        window.dispatchEvent(new Event('pi:unlocked'));"
)
(WEB / "gate.js").write_text(gate)
bb = (
    (ORIGINAL / "brandbook.html")
    .read_text()
    .replace("SOL · MAINNET", "BNB · PRE-LAUNCH")
    .replace("CONTRACT_ADDRESS · SOL", "CONTRACT_ADDRESS · BNB")
    .replace("Holders get paid every hour.", "Funded BNB settlement targets 15-minute rounds.")
    .replace("1d = 1.5× · 7d = 2.2× · 30d+ = 2.5× (cap)", "1d = 1× · 7d = 1.5× · 30d+ = 2× (cap)")
    .replace("📍 ", "")
    .replace("—", "-")
    .replace("–", "-")
)
(WEB / "brandbook.html").write_text(bb)
print(
    "Recovered frontend updated. Original styles, illustration classes and visual effect code retained."
)

# Keep the recovered fonts local and all review routes self-contained.
for name in ["index.html", "brandbook.html"]:
    p = WEB / name
    page = p.read_text()
    page = re.sub(
        r'<link[^>]+href="https://fonts\.googleapis\.com/css2[^>]+>',
        '<link rel="stylesheet" href="fonts.css" />',
        page,
    )
    page = re.sub(r'\s*<link[^>]+href="https://fonts\.(?:googleapis|gstatic)\.com"[^>]*>', "", page)
    page = page.replace(
        '<link rel="stylesheet" href="styles.css" />',
        '<link rel="stylesheet" href="styles.css" />\n  <link rel="stylesheet" href="bnb.css" />',
    )
    page = page.replace("<!-- left tank - HOLDERS 85% -->", "<!-- left tank - HOLDERS 70% -->")
    page = page.replace(">PI × w<", ">PI×w<")
    p.write_text(page)
bb = (WEB / "brandbook.html").read_text()
for old, new in [
    ("// SYS · MAINNET", "// SYS · BNB · REVIEW"),
    ("EVERY 1H · ALL HOLDERS", "15M TARGET · FUNDED ROUNDS"),
    ("EVERY 1H", "15M TARGET"),
    (">1h<", ">15m<"),
    (">1H<", ">15M<"),
    ("04:23:11", "00:14:59"),
    ("0x000000000000000000000000…", "NOT_DEPLOYED"),
    (
        "your_payout = pool × your_share × your_multiplier",
        "your_payout = funded_pool × your_weight / total_weight",
    ),
    ("Drop #00472 just landed.<br/>", "BNB reward distribution.<br/>"),
    (
        "3,142 wallets paid. Top earner held for 47 days.",
        "Funded entitlements, weighted by holding age. Review build.",
    ),
    ("// DROP_#00472 · COMPLETE", "// REWARD_MODEL · PRE-LAUNCH"),
    ("> SETTLED<", "> PENDING<"),
    (">3,142<", ">PENDING<"),
    (">$7,437<", ">0 BNB<"),
    (">$185<", ">0 BNB<"),
    (">$13.95<", ">0 BNB<"),
    ("T-MINUS the next drop.<br/>", "Funded settlement targets 15-minute rounds.<br/>"),
    ("Auto-claim. No action needed.", "Claim accrued BNB when you choose."),
    ("// T-MINUS · NEXT_DISTRIBUTION", "// TARGET · SETTLEMENT_WINDOW"),
    ('<span class="bb-gif-label">// LIVE</span>', '<span class="bb-gif-label">// REVIEW</span>'),
    ("pi-passive-income.io", "holdpi.com"),
    ("Published openly.", "Recovered visual reference with updated BNB model examples."),
    ("// TWEET · TEXT_ONLY", "// MOCKUP · TEXT_ONLY"),
    ("// TWEET · TEXT + VISUAL", "// MOCKUP · TEXT + VISUAL"),
    ("// TWEET · GIF", "// MOCKUP · MOTION"),
    ("💬", "↳"),
    ("📊", "▥"),
    ("🔗", "↗"),
    ("📅", ""),
]:
    bb = bb.replace(old, new)
(WEB / "brandbook.html").write_text(bb)

(WEB / "brandbook.js").write_text(
    (ORIGINAL / "brandbook.js")
    .read_text()
    .replace("const dropInterval = 1 * 3600;", "const dropInterval = 15 * 60;")
    .replace("same 1h cycle", "same 15-minute target")
)
