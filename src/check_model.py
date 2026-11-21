"""Deterministic economic scenarios and randomized ledger invariants."""

import json
import random
from pathlib import Path
from epoch_model import Model, DAY, TOKEN, exit_bps, birth_epoch


def paid_close(actual, expected):
    # Fractional wei remain owned in the account or rounding reserve.
    assert 0 <= expected - actual <= 1, (actual, expected)


def run():
    passed = []

    m = Model()
    m.buy("holder", 1000 * TOKEN)
    m.advance(31 * DAY)
    m.settle("holder")
    old = m.account("holder").mature
    m.buy("holder", 100 * TOKEN)
    assert m.account("holder").mature == old
    fee = m.sell("holder", 97 * TOKEN)
    assert fee == 97 * TOKEN * 1500 // 10000
    assert m.account("holder").mature == old
    m.audit()
    passed.append("Top-up preserves old lots; newest tokens pay the early exit fee")

    m.buy("donor", TOKEN)
    m.transfer("donor", "holder", 1000)
    assert m.account("holder").mature == old
    before = dict((b, l.amount) for b, l in m.account("holder").lots.items())
    assert m.transfer("holder", "holder", TOKEN) == 0
    assert m.transfer("donor", "holder", 0) == 0
    assert before == dict((b, l.amount) for b, l in m.account("holder").lots.items())
    m.audit()
    passed.append("Dust, zero transfers and self-transfers do not reset an old position")

    m = Model()
    m.buy("a", 100 * TOKEN)
    m.advance(31 * DAY)
    m.transfer("a", "b", 50 * TOKEN)
    assert m.weighted_supply() == m.account("a").mature * 25000
    assert all(birth == 31 for birth in m.account("b").lots)
    m.audit()
    passed.append("Transfer charges an exit and restarts recipient age; age cannot be forwarded")

    m = Model()
    m.buy("old", 100 * TOKEN)
    m.advance(29 * DAY)
    m.buy("young", 100 * TOKEN)
    m.advance(30 * DAY)
    m.fund_rewards(3500 * TOKEN)
    paid_close(m.claim("old"), 2500 * TOKEN)
    paid_close(m.claim("young"), 1000 * TOKEN)
    m.audit()
    passed.append("2.5x versus 1x weights divide the funded pool in a 2.5:1 ratio")

    m = Model()
    m.buy("a", 100 * TOKEN)
    m.buy("b", 100 * TOKEN)
    m.advance(31 * DAY)
    m.fund_rewards(1000 * TOKEN)
    paid_close(m.claim("a"), 500 * TOKEN)
    paid_close(m.claim("b"), 500 * TOKEN)
    m.audit()
    passed.append("Identical mature multipliers cancel; total rewards never multiply")

    m = Model()
    m.buy("a", 100 * TOKEN)
    m.advance(2 * DAY)
    m.fund_rewards(100 * TOKEN)
    m.buy("new", 100 * TOKEN)
    assert m.claim("new") == 0
    m.sell("a", m.account("a").balance)
    paid_close(m.claim("a"), 100 * TOKEN)
    m.audit()
    passed.append("New buyers receive no previous allocation; exiting cannot erase earned rewards")

    m = Model()
    m.fund_rewards(100 * TOKEN)
    m.buy("a", 100 * TOKEN)
    m.advance(DAY)
    m.fund_rewards(0)
    m.advance(365 * DAY)
    paid_close(m.claim("a"), 100 * TOKEN)
    assert m.claim("a") == 0
    m.audit()
    passed.append("No eligible holder preserves funds; long inactivity creates no new rewards")

    m = Model()
    m.buy("a", 100 * TOKEN)
    m.advance(DAY)
    m.fund_rewards(100 * TOKEN)
    m.advance(40 * DAY)
    m.fund_rewards(200 * TOKEN)
    paid_close(m.claim("a"), 300 * TOKEN)
    m.audit()
    passed.append("Lazy mature-cohort merge preserves historical and subsequent entitlements")

    for received in [1, DAY - 1, DAY, DAY + 1]:
        first_eligible = (birth_epoch(received) + 1) * DAY
        assert DAY <= first_eligible - received < 2 * DAY
    assert exit_bps(0) == 1500
    assert exit_bps(7) == 300
    assert exit_bps(300) == 300
    assert all(exit_bps(d + 1) <= exit_bps(d) for d in range(40))
    passed.append(
        "Conservative epoch rounding never grants a tier early; exit fee stays within 3%-15%"
    )

    m = Model()
    for day in range(100):
        m.advance(day * DAY + 1)
        m.buy("daily", 100 * TOKEN)
        m.fund_rewards(TOKEN)
        m.audit()
    assert len(m.account("daily").lots) <= 31
    passed.append(
        "Daily top-ups across 100 days remain bounded to 31 active cohorts plus mature balance"
    )

    def layered_position():
        item = Model()
        item.buy("a", 1000 * TOKEN)
        item.advance(31 * DAY)
        item.buy("a", 1000 * TOKEN)
        return item

    whole = layered_position()
    split = layered_position()
    whole_fee = whole.sell("a", 1500 * TOKEN)
    split_fee = split.sell("a", 600 * TOKEN) + split.sell("a", 900 * TOKEN)
    assert whole_fee == split_fee
    whole.audit()
    split.audit()
    passed.append("Splitting a sale does not let fresh inventory use a mature lot's cheaper fee")

    m = layered_position()
    before = m.weighted_supply()
    m.transfer("a", "unregistered_pool", 100 * TOKEN)
    assert m.weighted_supply() <= before
    fee = m.transfer("unregistered_pool", "buyer", m.account("unregistered_pool").balance)
    assert fee > 0
    m.audit()
    passed.append(
        "An unregistered intermediary remains subject to exit fees; transfers cannot create mature weight"
    )

    rng = random.Random(314159)
    m = Model()
    names = ["wallet_%02d" % i for i in range(40)]
    max_cohorts = 0
    for step in range(5000):
        m.advance(m.now + rng.randrange(0, 3600))
        name = rng.choice(names)
        action = rng.randrange(6)
        balance = m.account(name).balance
        if action == 0:
            m.buy(name, rng.randrange(1, 10000) * TOKEN)
        elif action == 1 and balance:
            m.sell(name, rng.randrange(1, balance + 1))
        elif action == 2 and balance:
            m.transfer(name, rng.choice(names), rng.randrange(1, balance + 1))
        elif action == 3:
            m.fund_rewards(rng.randrange(0, 1000) * TOKEN)
        elif action == 4:
            m.claim(name)
        elif action == 5:
            m.advance(m.now + rng.randrange(0, 2 * DAY))
        receipt = m.audit()
        max_cohorts = max(max_cohorts, receipt["max_wallet_active_cohorts"])
    passed.append(
        "5,000 randomized buys, sells, transfers, claims, fundings and time jumps conserve supply and rewards"
    )

    return {
        "status": "pass",
        "scenario_count": len(passed),
        "passed": passed,
        "random_seed": 314159,
        "random_events": 5000,
        "random_max_wallet_cohorts": max_cohorts,
        "final_ledger": m.audit(),
        "limits": [
            "Economic reference model only, not Solidity or EVM execution.",
            "No AMM price impact, market demand, MEV, gas benchmark or independent audit is proven.",
            "Received WETH is an external input representing already settled fee proceeds.",
        ],
    }


if __name__ == "__main__":
    result = run()
    output = Path(__file__).resolve().parents[1] / "outputs" / "model-checks.json"
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
