"""Executable economic reference model, not a deployed contract or an AMM.

Amounts use integer atomic units. Reward indices retain 36 decimal places.
Purchase cohorts use conservative UTC-day rounding. This model verifies ledger
rules; it does not measure EVM gas, execute swaps, or predict market demand.
"""

from dataclasses import dataclass, field

DAY = 86_400
TOKEN = 10**18
PRECISION = 10**36
SUPPLY = 1_000_000_000 * TOKEN
BUY_BPS = 300
MIN_EXIT_BPS = 300
MAX_EXIT_BPS = 1500
DECAY_DAYS = 7
MAX_AGE = 30


def birth_epoch(timestamp):
    return (timestamp + DAY - 1) // DAY


def age_days(timestamp, birth):
    return max(0, timestamp // DAY - birth)


def exit_bps(age):
    return MIN_EXIT_BPS + (MAX_EXIT_BPS - MIN_EXIT_BPS) * max(0, DECAY_DAYS - age) // DECAY_DAYS


def reward_weight(age):
    if age < 1:
        return 0
    if age < 7:
        return 10_000
    if age < 30:
        return 15_000
    return 25_000


@dataclass
class Lot:
    amount: int
    paid_index: int = 0


@dataclass
class Account:
    lots: dict = field(default_factory=dict)
    mature: int = 0
    mature_paid_index: int = 0
    earned_scaled: int = 0
    paid: int = 0

    @property
    def balance(self):
        return self.mature + sum(lot.amount for lot in self.lots.values())


class Model:
    def __init__(self, buy_bps=BUY_BPS, exit_rate=exit_bps, weight_rate=reward_weight):
        self.buy_bps = buy_bps
        self.exit_rate = exit_rate
        self.weight_rate = weight_rate
        self.mature_weight = weight_rate(MAX_AGE)
        self.now = 0
        self.accounts = {}
        self.pool_tokens = SUPPLY
        self.fee_tokens = 0
        self.global_lots = {}
        self.indices = {}
        self.merges = {}
        self.global_mature = 0
        self.mature_index = 0
        self.reward_funded = 0
        self.reward_paid = 0
        self.pending_reward = 0
        self.rounding_scaled = 0

    def account(self, name):
        if name not in self.accounts:
            self.accounts[name] = Account(mature_paid_index=self.mature_index)
        return self.accounts[name]

    def advance(self, timestamp):
        assert timestamp >= self.now
        self.now = timestamp
        self._roll()

    def _roll(self):
        for birth in list(self.global_lots):
            if age_days(self.now, birth) >= MAX_AGE:
                self.merges[birth] = (self.indices.get(birth, 0), self.mature_index)
                self.global_mature += self.global_lots.pop(birth)

    def settle(self, name):
        self._roll()
        a = self.account(name)
        a.earned_scaled += a.mature * (self.mature_index - a.mature_paid_index)
        a.mature_paid_index = self.mature_index
        for birth, lot in list(a.lots.items()):
            if birth in self.merges:
                final_index, merge_mature_index = self.merges[birth]
                effective_index = final_index + self.mature_index - merge_mature_index
                a.earned_scaled += lot.amount * (effective_index - lot.paid_index)
                a.mature += lot.amount
                del a.lots[birth]
            else:
                index = self.indices.get(birth, 0)
                a.earned_scaled += lot.amount * (index - lot.paid_index)
                lot.paid_index = index
        return a

    def _receive(self, name, amount):
        if amount == 0:
            return
        a = self.settle(name)
        birth = birth_epoch(self.now)
        if birth not in a.lots:
            a.lots[birth] = Lot(0, self.indices.get(birth, 0))
        a.lots[birth].amount += amount
        self.global_lots[birth] = self.global_lots.get(birth, 0) + amount
        assert len(a.lots) <= 31

    def buy(self, name, gross_tokens):
        assert 0 <= gross_tokens <= self.pool_tokens
        if gross_tokens == 0:
            return 0
        fee = gross_tokens * self.buy_bps // 10_000
        self.pool_tokens -= gross_tokens
        self.fee_tokens += fee
        self._receive(name, gross_tokens - fee)
        return fee

    def _exit(self, name, amount):
        a = self.settle(name)
        assert 0 <= amount <= a.balance
        left = amount
        fee = 0
        # Newest acquisition is consumed first. An old wallet cannot season a
        # new acquisition merely by receiving it.
        for birth in sorted(a.lots, reverse=True):
            if not left:
                break
            lot = a.lots[birth]
            take = min(left, lot.amount)
            fee += take * self.exit_rate(age_days(self.now, birth)) // 10_000
            lot.amount -= take
            self.global_lots[birth] -= take
            left -= take
            if lot.amount == 0:
                del a.lots[birth]
        if left:
            assert left <= a.mature
            fee += left * self.exit_rate(MAX_AGE) // 10_000
            a.mature -= left
            self.global_mature -= left
        self.fee_tokens += fee
        return amount - fee, fee

    def sell(self, name, amount):
        net, fee = self._exit(name, amount)
        self.pool_tokens += net
        return fee

    def transfer(self, sender, recipient, amount):
        assert 0 <= amount <= self.account(sender).balance
        if amount == 0 or sender == recipient:
            return 0
        net, fee = self._exit(sender, amount)
        self._receive(recipient, net)
        return fee

    def weighted_supply(self):
        self._roll()
        return self.global_mature * self.mature_weight + sum(
            amount * self.weight_rate(age_days(self.now, birth))
            for birth, amount in self.global_lots.items()
        )

    def fund_rewards(self, received_quote):
        """Credit quote assets actually received after processing; no assumed USD price."""
        assert received_quote >= 0
        self.reward_funded += received_quote
        available = received_quote + self.pending_reward
        weight = self.weighted_supply()
        if not weight:
            self.pending_reward = available
            return
        self.pending_reward = 0
        # Carry complete rounding units into the next funded allocation.
        recycled = self.rounding_scaled // PRECISION
        self.rounding_scaled -= recycled * PRECISION
        available += recycled
        allocated_scaled = 0
        for birth, amount in self.global_lots.items():
            delta = available * self.weight_rate(age_days(self.now, birth)) * PRECISION // weight
            self.indices[birth] = self.indices.get(birth, 0) + delta
            allocated_scaled += amount * delta
        mature_delta = available * self.mature_weight * PRECISION // weight
        self.mature_index += mature_delta
        allocated_scaled += self.global_mature * mature_delta
        self.rounding_scaled += available * PRECISION - allocated_scaled

    def claim(self, name):
        a = self.settle(name)
        amount = a.earned_scaled // PRECISION
        assert amount <= self.reward_funded - self.reward_paid
        a.earned_scaled -= amount * PRECISION
        a.paid += amount
        self.reward_paid += amount
        return amount

    def audit(self):
        for name in list(self.accounts):
            self.settle(name)
        assert (
            self.pool_tokens + self.fee_tokens + sum(a.balance for a in self.accounts.values())
            == SUPPLY
        )
        assert self.global_mature == sum(a.mature for a in self.accounts.values())
        manual_lots = {}
        for a in self.accounts.values():
            assert a.balance >= 0 and a.earned_scaled >= 0
            assert len(a.lots) <= 31
            for birth, lot in a.lots.items():
                manual_lots[birth] = manual_lots.get(birth, 0) + lot.amount
        assert {k: v for k, v in self.global_lots.items() if v} == manual_lots
        obligations = sum(a.earned_scaled for a in self.accounts.values())
        cash = (self.reward_funded - self.reward_paid) * PRECISION
        assert cash == obligations + self.pending_reward * PRECISION + self.rounding_scaled
        assert self.reward_paid <= self.reward_funded
        assert len(self.global_lots) <= 31
        return {
            "holders": len(self.accounts),
            "active_global_cohorts": len(self.global_lots),
            "max_wallet_active_cohorts": max(
                (len(a.lots) for a in self.accounts.values()), default=0
            ),
            "reward_funded_wei": self.reward_funded,
            "reward_paid_wei": self.reward_paid,
            "pending_reward_wei": self.pending_reward,
        }
