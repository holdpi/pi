const { test } = require("node:test");
const assert = require("node:assert/strict");
const model = require("../website/economics.js");
const base = {
  holdings: 1_000_000,
  days: 30,
  volume: 100,
  buyFraction: 0.5,
  averageSellBps: 400,
  otherWeight: 500_000_000,
  conversionLoss: 0.005,
};
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-10, `${a} != ${b}`);
test("matches all specified fee checkpoints and never increases with age", () => {
  const points = [
    [0, 1000],
    [1, 800],
    [3, 600],
    [7, 400],
    [14, 200],
    [30, 100],
    [365, 100],
  ];
  for (const [d, r] of points) assert.equal(model.sellBps(d), r);
  for (let d = 1; d < 366; d++)
    assert.ok(model.sellBps(d) <= model.sellBps(d - 1));
});
test("has no funded share before qualification", () =>
  assert.equal(model.calculate({ ...base, days: 0 }).payout, 0));
test("matches the finite 100 BNB reference scenario", () => {
  const p = model.calculate(base);
  near(p.gross, 4.5);
  near(p.received, 4.4775);
  near(p.holderPool, 3.13425);
  near(p.buyback, 0.671625);
  near(p.liquidity, 0.44775);
  near(p.operations, 0.223875);
  near(p.holderPool + p.buyback + p.liquidity + p.operations, p.received);
});
test("a sole eligible holder receives exactly the holder pot, never a weight-multiplied pot", () => {
  for (const days of [1, 7, 30]) {
    const p = model.calculate({ ...base, otherWeight: 0, days });
    near(p.payout, p.holderPool);
  }
});
test("two equal PI balances at 2x and 1x divide a single pot 2 to 1", () => {
  const a = model.calculate({
    ...base,
    holdings: 100,
    days: 30,
    otherWeight: 100,
  });
  const b = model.calculate({
    ...base,
    holdings: 100,
    days: 1,
    otherWeight: 200,
  });
  near(a.payout, 2 * b.payout);
  near(a.payout + b.payout, a.holderPool);
});
test("no volume and full conversion loss produce no invented payout", () => {
  assert.equal(model.calculate({ ...base, volume: 0 }).payout, 0);
  assert.equal(model.calculate({ ...base, conversionLoss: 1 }).payout, 0);
});
test("nonfinite and extreme input cannot produce a nonfinite output", () => {
  for (const input of [NaN, Infinity, -Infinity, -1, 1e308])
    for (const key of Object.keys(base)) {
      const p = model.calculate({ ...base, [key]: input });
      for (const value of Object.values(p)) assert.ok(Number.isFinite(value));
      assert.ok(p.payout >= 0 && p.payout <= p.holderPool);
    }
});
