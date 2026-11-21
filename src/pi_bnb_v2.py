"""PI v2 economic calibration. Amounts are scenarios, never demand forecasts.

Reuses the bounded, conservative daily-cohort ledger. Prices and fee conversion
are external inputs; this program is not an AMM, deployed Solidity or a gas test.
"""
import json
import random
from fractions import Fraction
from pathlib import Path

from epoch_model import Model, DAY, TOKEN, PRECISION, birth_epoch

BUY_BPS = 500
SELL_KNOTS = [(0, 1000), (1, 800), (3, 600), (7, 400), (14, 200), (30, 100)]
SPLIT = {"holders": 70, "buyback_burn": 15, "liquidity": 10, "operations": 5}


def sell_bps(days):
    """Daily interpolation, rounded up to the next bps until the exact knot."""
    days = max(0, days)
    for (start, high), (end, low) in zip(SELL_KNOTS, SELL_KNOTS[1:]):
        if days < end:
            return high - (high - low) * (days - start) // (end - start)
    return 100


def weight_bps(days):
    if days < 1:
        return 0
    if days < 7:
        return 10000
    if days < 30:
        return 15000
    return 20000


def model():
    return Model(buy_bps=BUY_BPS, exit_rate=sell_bps, weight_rate=weight_bps)


class Budgets:
    """Disjoint cumulative allocations with explicit quote-asset dust carry."""
    def __init__(self):
        self.received = 0
        self.allocated = {k: 0 for k in SPLIT}
        self.spent = {k: 0 for k in SPLIT}

    def credit(self, received):
        assert received >= 0
        self.received += received
        increments = {}
        for name, percent in SPLIT.items():
            target = self.received * percent // 100
            increments[name] = target - self.allocated[name]
            self.allocated[name] = target
        self.audit()
        return increments

    def spend(self, name, amount):
        assert 0 <= amount <= self.allocated[name] - self.spent[name]
        self.spent[name] += amount
        self.audit()

    def audit(self):
        dust = self.received - sum(self.allocated.values())
        assert 0 <= dust < len(SPLIT)
        assert all(0 <= self.spent[k] <= self.allocated[k] for k in SPLIT)
        cash = self.received - sum(self.spent.values())
        assert cash == dust + sum(self.allocated[k] - self.spent[k] for k in SPLIT)


def economics(volume, avg_sell_bps=400, buy_fraction=Fraction(1, 2), buy_bps=BUY_BPS):
    rate = buy_fraction * buy_bps + (1 - buy_fraction) * avg_sell_bps
    fees = Fraction(volume) * rate / 10000
    return {
        "trading_volume_usd": volume,
        "buy_volume_fraction": float(buy_fraction),
        "average_sell_tax_pct": float(Fraction(avg_sell_bps,100)),
        "blended_project_tax_pct": float(rate / 100),
        "gross_project_fee_value_usd": float(fees),
        "budgets_usd": {k: float(fees * p / 100) for k, p in SPLIT.items()},
    }


def checks():
    passed = []
    assert sum(SPLIT.values()) == 100
    assert all(sell_bps(d) == bps for d,bps in SELL_KNOTS)
    assert all(100 <= sell_bps(d) <= 1000 for d in range(365))
    assert all(sell_bps(d+1) <= sell_bps(d) for d in range(365))
    assert max(sell_bps(d)-sell_bps(d+1) for d in range(30)) == 200
    passed.append("Daily sell tax decreases from 10 percent to 1 percent, never exceeds the cap, and stays at the floor after maturity")

    b = Budgets()
    for _ in range(101):
        b.credit(1)
    assert b.allocated == {"holders":70,"buyback_burn":15,"liquidity":10,"operations":5}
    b.spend("operations",5)
    try:
        b.spend("operations",1)
        raise AssertionError("Overspend should have failed")
    except AssertionError as e:
        if str(e) == "Overspend should have failed": raise
    b.audit()
    passed.append("70/15/10/5 budgets conserve cash and dust; operations cannot spend other allocations")

    for purchase_day in (0, 20, 365):
        for offset in (123, DAY - 1):
            m = model()
            received = purchase_day * DAY + offset
            m.advance(received)
            assert m.buy("fresh", 1000 * TOKEN) == 50 * TOKEN
            m.advance(received + DAY - 1)
            assert m.sell("fresh", 950 * TOKEN) == 95 * TOKEN
            m.audit()
    passed.append("Launch day, day 20 and day 365 purchases all pay 5 percent on entry and 10 percent on exit within 24 hours, including across midnight")

    m = model()
    fee = m.buy("old",1000*TOKEN)
    assert fee == 50*TOKEN
    m.advance(31*DAY)
    old = m.settle("old").mature
    m.buy("old",100*TOKEN)
    assert m.account("old").mature == old
    assert m.sell("old",95*TOKEN) == Fraction(95*TOKEN,10)
    assert m.account("old").mature == old
    m.audit()
    passed.append("Top-ups preserve old holdings; fresh tokens cannot inherit a mature position's 1 percent sell tax")

    m = model()
    m.buy("old",100*TOKEN)
    m.advance(29*DAY)
    m.buy("young",100*TOKEN)
    m.advance(30*DAY)
    m.fund_rewards(300*TOKEN)
    old_paid, young_paid = m.claim("old"),m.claim("young")
    assert 0 <= 200*TOKEN-old_paid <= 1
    assert 0 <= 100*TOKEN-young_paid <= 1
    m.audit()
    passed.append("A 2x mature holder and equal-sized 1x holder divide a finite reward budget 2:1")

    m = model()
    m.buy("a",100*TOKEN)
    m.buy("b",100*TOKEN)
    m.advance(31*DAY)
    m.fund_rewards(100*TOKEN)
    assert 0 <= 50*TOKEN-m.claim("a") <= 1
    assert 0 <= 50*TOKEN-m.claim("b") <= 1
    m.audit()
    passed.append("When everybody matures the multipliers cancel; total payments do not double")

    m = model()
    m.fund_rewards(70*TOKEN)
    assert m.pending_reward == 70*TOKEN
    m.buy("a",100*TOKEN)
    assert m.claim("a") == 0
    m.advance(DAY)
    m.fund_rewards(0)
    m.sell("a",m.account("a").balance)
    assert 0 <= 70*TOKEN-m.claim("a") <= 1
    m.advance(365*DAY)
    assert m.claim("a") == 0
    m.audit()
    passed.append("No eligible holders preserves the reward reserve; selling preserves earned rewards; time without funding creates no new liability")

    m = model()
    m.buy("a",100*TOKEN)
    m.advance(31*DAY)
    mature_before = m.settle("a").mature
    assert m.transfer("a","a",TOKEN) == 0
    assert m.account("a").mature == mature_before
    assert m.transfer("a","b",50*TOKEN) == TOKEN//2
    assert m.account("b").mature == 0
    assert m.sell("b",m.account("b").balance) == 495*TOKEN//100
    m.audit()
    passed.append("Self-transfers preserve age; moving tokens pays the exit fee and creates fresh recipient age")

    for received in (1,DAY-1,DAY,DAY+1):
        first = (birth_epoch(received)+1)*DAY
        last = (birth_epoch(received)+30)*DAY
        assert DAY <= first-received < 2*DAY
        assert 30*DAY <= last-received < 31*DAY
    passed.append("Conservative daily buckets never grant an early tier; the exact 1 percent transition is 30 to under 31 days from receipt")

    rng=random.Random(271828)
    m=model()
    b=Budgets()
    names=["holder_%02d" % i for i in range(40)]
    max_cohorts=0
    for step in range(10000):
        m.advance(m.now+rng.randrange(0,3600))
        name=rng.choice(names)
        balance=m.account(name).balance
        action=rng.randrange(7)
        if action==0:
            m.buy(name,rng.randrange(1,10000)*TOKEN)
        elif action==1 and balance:
            m.sell(name,rng.randrange(1,balance+1))
        elif action==2 and balance:
            m.transfer(name,rng.choice(names),rng.randrange(1,balance+1))
        elif action==3:
            # Only assets already received may fund budget accounting.
            inc=b.credit(rng.randrange(0,1000)*TOKEN)
            b.spend("holders",inc["holders"])
            m.fund_rewards(inc["holders"])
        elif action==4:
            m.claim(name)
        elif action==5:
            m.advance(m.now+rng.randrange(0,2*DAY))
        else:
            bucket=rng.choice(["buyback_burn","liquidity","operations"])
            available=b.allocated[bucket]-b.spent[bucket]
            b.spend(bucket,rng.randrange(0,available+1))
        result=m.audit()
        b.audit()
        assert m.reward_funded==b.spent["holders"]
        max_cohorts=max(max_cohorts,result["max_wallet_active_cohorts"])
    passed.append("10,000 randomized funded allocations, buys, sells, transfers, claims, bucket spending and time jumps preserve supply and liabilities")
    return {"status":"pass","checks":passed,"random_events":10000,"random_seed":271828,
            "max_wallet_cohorts":max_cohorts,"ledger":m.audit()}


def calibration():
    profiles={
        "fast_exits": [(0,50),(1,20),(3,15),(7,10),(14,4),(30,1)],
        "mixed_exits": [(0,20),(1,15),(3,15),(7,20),(14,15),(30,15)],
        "patient_exits": [(0,5),(1,5),(3,10),(7,20),(14,20),(30,40)],
        "all_mature": [(30,100)],
    }
    choices={"front_loaded_daily":sell_bps,"linear_30_day":lambda d:max(100,1000-30*d)}
    comparisons=[]
    for schedule,fn in choices.items():
        for label,profile in profiles.items():
            avg=sum(Fraction(fn(d)*p,100) for d,p in profile)
            for buy in (200,300,500):
                comparisons.append({"schedule":schedule,"seller_profile":label,"buy_tax_pct":buy/100,
                                    **economics(100000,avg,buy_bps=buy)})
    scenarios=[economics(v,s) for v in (0,1000,10000,100000,1000000) for s in (100,400,1000)]
    friction=[]
    for days,sell in SELL_KNOTS:
        # DEX: fixed-price small-trade approximation, project fees only.
        value=Fraction(100)*(1-Fraction(BUY_BPS,10000))*(1-Fraction(sell,10000))
        # Bonding: gross input includes project + observed 1 percent platform fee.
        bond=Fraction(100)/(1+Fraction(BUY_BPS+100,10000))*(1-Fraction(sell+100,10000))
        friction.append({"holding_days":days,"sell_tax_pct":sell/100,
                         "dex_value_after_100_usd_roundtrip_project_fees_only":float(value),
                         "dex_price_increase_to_break_even_pct":float((100/value-1)*100),
                         "bonding_value_after_100_usd_roundtrip_with_platform_fees":float(bond)})
    # Higher tax raises receipts only if enough trading volume is retained.
    buy_sensitivity=[]
    for avg in (100,400,1000):
        for lower_buy, higher_buy in ((200,300),(200,500),(300,500)):
            low=Fraction(lower_buy+avg,2)
            high=Fraction(higher_buy+avg,2)
            buy_sensitivity.append({"average_sell_tax_pct":avg/100,
                                    "lower_buy_tax_pct":lower_buy/100,
                                    "higher_buy_tax_pct":higher_buy/100,
                                    "volume_loss_fraction_wiping_out_extra_revenue":float(1-low/high)})
    ops=[]
    for fees in (0,30,300,3000):
        for cost in (Fraction(2,100),Fraction(1,10)):
            daily_gas_limit=Fraction(fees,100)
            ops.append({"daily_received_project_fees_usd":fees,"assumed_batch_cost_usd":float(cost),
                        "daily_processing_budget_usd":float(daily_gas_limit),
                        "max_batches_per_day_within_budget":min(96,int(daily_gas_limit/cost)),
                        "minimum_fee_batch_usd":float(cost*100)})
    return {"selected_buy_bps":BUY_BPS,"sell_checkpoints":SELL_KNOTS,"allocation_pct":SPLIT,
            "curve_comparisons":comparisons,"volume_scenarios":scenarios,"roundtrip_friction":friction,
            "buy_tax_sensitivity":buy_sensitivity,"processing_scenarios":ops,
            "central_example":economics(100000,400),
            "mature_example":economics(100000,100),
            "limits":["Volume and seller ages are explicit assumptions, not forecasts or evidence of an optimal market response.",
                      "Budget illustrations use gross tax value with frictionless conversion. Production splits only realized quote proceeds; conversion fees and slippage reduce receipts.",
                      "DEX round trips assume unchanged price, negligible price impact and exclude AMM/gas fees; bonding additionally models the observed 1 percent platform fee with anti-sniper disabled.",
                      "Batch-cost dollar values are sensitivity inputs, not current BNB gas quotations.",
                      "Rewards are WBNB-backed liabilities with optional native BNB withdrawal, not USD promises."]}


if __name__=="__main__":
    out={"version":"PI BNB economics v2","calibration":calibration(),"verification":checks()}
    path=Path(__file__).resolve().parents[1]/"outputs/pi-bnb-v2-calculations.json"
    path.write_text(json.dumps(out,indent=2))
    print(json.dumps({"verification":out["verification"],
                      "central_example":out["calibration"]["central_example"],
                      "mature_example":out["calibration"]["mature_example"],
                      "friction":out["calibration"]["roundtrip_friction"],
                      "buy_tax_sensitivity":out["calibration"]["buy_tax_sensitivity"]},indent=2))
