const { test } = require("node:test");
const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const M = require("../website/protocol-model.js");
const Z = require("../website/protocol-zip.js");
test("the default protocol reproduces PI daily sell checkpoints and loyalty weights", () => {
  const p = M.policy(M.DEFAULTS);
  assert.deepEqual(
    [0, 1, 3, 7, 14, 30].map((i) => p.sellBps[i]),
    [1000, 800, 600, 400, 200, 100],
  );
  assert.deepEqual(
    [0, 1, 7, 30].map((i) => p.weightBps[i]),
    [0, 10000, 15000, 20000],
  );
  assert.deepEqual(p.splitBps, [7000, 1500, 1000, 500]);
});
test("every supported curve remains bounded, descending and reaches its floor", () => {
  for (const curve of ["pi", "linear", "early", "late"])
    for (let decayDays = 1; decayDays <= 30; decayDays++)
      for (const sellFloor of [0, 0.25, 1, 9.75, 10]) {
        const t = M.sellTable({ ...M.DEFAULTS, curve, decayDays, sellFloor });
        assert.equal(t[0], 1000);
        assert.equal(t[decayDays], sellFloor * 100);
        t.forEach((v, i) => {
          assert(Number.isInteger(v) && v >= sellFloor * 100 && v <= 1000);
          if (i) assert(v <= t[i - 1]);
        });
      }
});
test("custom qualification and weights are bounded and never reward an immature purchase", () => {
  for (let qualificationDays = 1; qualificationDays <= 30; qualificationDays++)
    for (const rewardCurve of ["pi", "linear"]) {
      const t = M.weightTable({
        ...M.DEFAULTS,
        qualificationDays,
        loyaltyDays: 30,
        maxWeight: 5,
        rewardCurve,
      });
      for (let i = 0; i < qualificationDays; i++) assert.equal(t[i], 0);
      assert.equal(t[30], 50000);
      t.forEach((v, i) => {
        assert(Number.isInteger(v));
        if (i) assert(v >= t[i - 1]);
      });
    }
});
test("rejects over-allocated, increasing-tax and malformed imported configurations", () => {
  for (const patch of [
    { holders: 71 },
    { sellFloor: 10, sellStart: 1 },
    { roundMinutes: 0 },
    { qualificationDays: 0 },
    { minFunding: "-1" },
    { maxWeight: 6 },
    { name: "" },
    { symbol: "<script>" },
    { supply: "1000000000001" },
  ])
    assert(M.validate({ ...M.DEFAULTS, ...patch }).length > 0);
  assert.throws(() => M.importConfig({ schema: "other", settings: {} }));
  assert.throws(() =>
    M.importConfig({
      schema: M.VERSION,
      settings: { ...M.DEFAULTS, curve: "malicious" },
    }),
  );
});
test("conserves fee revenue and gives zero new reward with zero volume", () => {
  const s = { ...M.DEFAULTS },
    r = M.result(s);
  assert.equal(r.gross, 4.5);
  assert.equal(r.net, 4.4775);
  assert(Math.abs(r.split.reduce((a, b) => a + b, 0) - r.net) < 1e-12);
  assert.equal(M.result({ ...s, volume: 0 }).payout, 0);
  assert.equal(M.result({ ...s, holdingDays: 0 }).payout, 0);
  assert.equal(M.result({ ...s, minFunding: "100" }).canSettle, false);
  assert(r.payout <= r.split[0]);
});
test("config round-trip preserves exact integer policy and consistent bonding inventory", () => {
  const s = {
    ...M.DEFAULTS,
    curve: "late",
    buy: 2.75,
    sellStart: 9.75,
    sellFloor: 0.25,
    decayDays: 17,
    roundMinutes: 60,
    holders: 60,
    burn: 20,
    liquidity: 15,
    operations: 5,
    name: "A different token",
    symbol: "WAIT",
    supply: "12345",
    raiseBNB: "200",
  };
  const c = M.exportConfig(s);
  assert.deepEqual(M.importConfig(JSON.parse(JSON.stringify(c))), s);
  assert.equal(BigInt(c.token.saleAmount) * 5n, BigInt(c.token.maxSupply) * 4n);
  assert.equal(BigInt(c.token.virtualQuote) * 4n, BigInt(c.token.raiseAmount));
  assert.equal(c.policy.buyBps, 275);
  assert.equal(c.policy.roundSeconds, 3600);
});
test("ZIP CRC is standard and personalized pack contains the exact configuration", () => {
  assert.equal(Z.crc32(new TextEncoder().encode("123456789")), 0xcbf43926);
  const archive = path.resolve(
    __dirname,
    "../website/review/holdpi-protocol-review.zip",
  );
  const config = M.exportConfig(M.DEFAULTS);
  const packed = Z.append(
    fs.readFileSync(archive),
    "configuration.json",
    JSON.stringify(config),
  );
  const readConfig = `
import io
import sys
import zipfile

with zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read())) as archive:
    assert archive.testzip() is None
    sys.stdout.buffer.write(archive.read('configuration.json'))
`;
  const extracted = execFileSync("python3", ["-c", readConfig], {
    input: packed,
    encoding: "utf8",
  });
  assert.deepEqual(JSON.parse(extracted), config);
});
