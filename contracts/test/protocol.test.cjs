const { expect } = require("chai");
const { ethers, artifacts } = require("hardhat");
const {
  time,
  loadFixture,
} = require("@nomicfoundation/hardhat-network-helpers");
const {
  base,
  buy,
  fund,
  E,
  DAY,
  deploy,
  graduated,
  dexBuy,
  dexSell,
  oracle,
} = require("./protocol-fixtures.cjs");
const M = require("../../website/protocol-model.js");
const birth = (timestamp) => Math.ceil(timestamp / DAY) * DAY;
async function custom() {
  return base({
    buy: 2.5,
    sellStart: 8,
    sellFloor: 0.5,
    curve: "linear",
    decayDays: 12,
    roundMinutes: 60,
    qualificationDays: 3,
    loyaltyDays: 12,
    maxWeight: 3,
    rewardCurve: "linear",
    holders: 60,
    burn: 20,
    liquidity: 15,
    operations: 5,
    minFunding: "0.1",
    name: "Patient Token",
    symbol: "WAIT",
  });
}
describe("HoldPI configurable protocol", function () {
  it("keeps implementation bytecode deployable and round-trips the official token tuple schema", async () => {
    const c = await loadFixture(base),
      module = c.implementations.at(-1);
    for (const n of [
      "HoldToken",
      "HoldRewards",
      "HoldTreasury",
      "HoldTradeModule",
      "HoldTokenModule",
      "HoldPresetValidator",
      "HoldVault",
      "HoldCurveModule",
      "HoldMigrateModule",
    ]) {
      const a = await artifacts.readArtifact(n);
      expect((a.deployedBytecode.length - 2) / 2, n).at.most(24576);
    }
    const schema = await module.moduleEncodeSchema();
    expect(schema.kind).eq("token");
    const tuple =
      "tuple(" +
      schema.params.map((x) => x.abiType + " " + x.name).join(",") +
      ")";
    expect(tuple).eq(M.TOKEN_TYPE);
    const d = ethers.AbiCoder.defaultAbiCoder().decode([tuple], c.config)[0];
    expect(d.buyBps).eq(500);
    expect([...d.sellBps].map(Number)).deep.eq(M.sellTable(M.DEFAULTS));
    expect([...d.weightBps].map(Number)).deep.eq(M.weightTable(M.DEFAULTS));
    expect(await c.token.policyHash()).eq(ethers.keccak256(c.config));
    for (const [index, kind, count] of [
      [1, "vault", 0],
      [2, "curve", 2],
      [3, "trade", 0],
      [4, "migrate", 0],
    ]) {
      const schema = await c.implementations[index].moduleEncodeSchema();
      expect(schema.kind).eq(kind);
      expect(schema.params.length).eq(count);
    }
  });
  it("applies custom buy and per-purchase sell rates on launch day and day 20", async () => {
    const c = await loadFixture(custom),
      token = await c.token.getAddress();
    const q = await c.core.preview(token, c.alice.address, E("1000"), true);
    expect(q[1]).eq((q[0] * 250n) / 10000n);
    await buy(c, c.alice, "1000");
    expect(await c.token.exitFeeBps(c.alice.address, E("1000"))).eq(800);
    await time.increase(20 * DAY);
    await buy(c, c.bob, "1000");
    expect(await c.token.exitFeeBps(c.bob.address, E("1000"))).eq(800);
    expect(await c.token.exitFeeBps(c.alice.address, E("1000"))).eq(50);
    await buy(c, c.alice, "100");
    expect(await c.token.exitFeeBps(c.alice.address, E("100"))).eq(800);
    await c.core.connect(c.alice).sell(token, E("100"));
    expect(await c.token.exitFeeBps(c.alice.address, E("1000"))).eq(50);
  });
  it("uses the exact daily sell and weight arrays exported by the UI", async () => {
    const c = await loadFixture(custom);
    await buy(c, c.alice, "1000");
    const born = birth(await time.latest());
    for (let d = 0; d <= 30; d++) {
      if (d) await time.increaseTo(born + d * DAY);
      expect(await c.token.exitFeeBps(c.alice.address, E("1000"))).eq(
        c.selected.policy.sellBps[d],
      );
      expect(await c.rewards.weightBps(d)).eq(c.selected.policy.weightBps[d]);
    }
  });
  it("requires both eligibility and minimum funding, then enforces custom cadence", async () => {
    const c = await loadFixture(custom);
    await buy(c, c.alice, "1000");
    const born = birth(await time.latest());
    await fund(c, "0.01");
    expect(await c.rewards.distribute.staticCall()).eq(0);
    await time.increaseTo(born + 3 * DAY);
    expect(await c.rewards.distribute.staticCall()).eq(0);
    await fund(c, "1");
    const funded = await c.rewards.funded();
    await c.rewards.distribute();
    expect(await c.rewards.claimable(c.alice.address)).closeTo(funded, 1n);
    await expect(c.rewards.distribute()).revertedWith("HOLD: round not due");
    await time.increase(3600);
    expect(await c.rewards.distribute.staticCall()).eq(0);
  });
  it("divides actual BNB funding by the configured 3x and 1x weights", async () => {
    const c = await loadFixture(custom);
    await buy(c, c.alice, "1000");
    await time.increase(31 * DAY);
    await buy(c, c.bob, "1000");
    await time.increaseTo(birth(await time.latest()) + 3 * DAY);
    await fund(c, "2");
    await c.rewards.distribute();
    const a = await c.rewards.claimable(c.alice.address),
      b = await c.rewards.claimable(c.bob.address);
    expect(a).closeTo(b * 3n, 4n);
    expect(a + b).at.most(await c.rewards.funded());
    const before = await c.quote.balanceOf(c.alice.address);
    await c.rewards.connect(c.alice).claim(c.alice.address, false);
    expect((await c.quote.balanceOf(c.alice.address)) - before).eq(a);
  });
  it("allocates the selected treasury percentages without crossing budgets", async () => {
    const c = await loadFixture(custom);
    await c.quote.transfer(await c.treasury.getAddress(), E("10"));
    await c.treasury.sync();
    for (let i = 0; i < 4; i++)
      expect(await c.treasury.available(i)).eq(E(["6", "2", "1.5", "0.5"][i]));
    await expect(
      c.treasury.connect(c.ops).withdrawOperations(E("0.51")),
    ).revertedWith("HOLD: operations budget");
    await expect(c.treasury.fundHolders(E("6.1"))).revertedWith(
      "HOLD: holder budget",
    );
    await c.treasury.fundHolders(E("6"));
    expect(await c.rewards.pending()).eq(E("6"));
    expect(await c.treasury.available(1)).eq(E("2"));
  });
  it("does not transfer acquisition age, and protects initialization from unrelated callers", async () => {
    const c = await loadFixture(custom);
    await buy(c, c.alice, "1000");
    await time.increase(31 * DAY);
    await c.token.connect(c.alice).transfer(c.bob.address, E("100"));
    expect(await c.token.balanceOf(c.bob.address)).eq(E("99.5"));
    expect(await c.token.exitFeeBps(c.bob.address, E("99.5"))).eq(800);
    await expect(
      c.rewards.initialize(
        c.alice.address,
        await c.quote.getAddress(),
        await c.treasury.getAddress(),
        c.selected.policy.sellBps,
        c.selected.policy.weightBps,
        60,
        0,
      ),
    ).revertedWith("Initializable: contract is already initialized");
    const code = await artifacts.readArtifact("HoldToken");
    expect(
      code.abi.some((x) =>
        /^set(Buy|Sell|Tax|Fee|Policy|Round|Weight|Split)/i.test(x.name || ""),
      ),
    ).eq(false);
    const trade = await ethers.getContractAt(
      "HoldTradeModule",
      await c.token.tradeModule(),
    );
    const denial = await trade.evaluate([
      await c.token.getAddress(),
      c.carol.address,
      1,
      false,
      await time.latest(),
      1,
      1,
      0,
      1,
      "0x",
    ]);
    expect(denial.allowed).eq(false);
  });
  it("rejects invalid curves, funding cadence and split before token creation", async () => {
    const c = await loadFixture(base),
      bindings = {
        core: await c.core.getAddress(),
        rewardsImplementation: await c.rewardsImpl.getAddress(),
        treasuryImplementation: await c.treasuryImpl.getAddress(),
        router: await c.router.getAddress(),
        operations: c.ops.address,
      };
    const cases = [
      (p) => (p.buyBps = 1001),
      (p) => (p.sellBps[3] = 1001),
      (p) => (p.sellBps[3] = 900),
      (p) => (p.weightBps[0] = 10000),
      (p) => (p.weightBps[30] = 50001),
      (p) => (p.weightBps[9] = 0),
      (p) => (p.roundSeconds = 59),
      (p) => (p.splitBps[0] = 7001),
      (p) => p.sellBps.pop(),
      (p) => p.weightBps.pop(),
      (p) => (p.roundSeconds = 86401),
      (p) => (p.minFunding = (10n ** 24n + 1n).toString()),
      (p) => (p.weightBps[30] = 9999),
      (p) => p.splitBps.pop(),
      (p) => (p.splitBps = [0, 0, 0, 0]),
    ];
    for (const mutate of cases) {
      const cfg = structuredClone(c.selected);
      mutate(cfg.policy);
      const args = {
        ...c.create,
        tokenParams: M.encodeToken(ethers, cfg, bindings),
      };
      await expect(
        c.core.launch(
          await Promise.all(c.implementations.map((x) => x.getAddress())),
          args,
          c.curveParams,
        ),
      ).reverted;
    }
  });
  it("validates the exported launch tuple and rejects mismatched infrastructure and inventory", async () => {
    const c = await loadFixture(custom),
      b = {
        core: await c.core.getAddress(),
        quoteAsset: await c.quote.getAddress(),
        rewardsImplementation: await c.rewardsImpl.getAddress(),
        treasuryImplementation: await c.treasuryImpl.getAddress(),
        router: await c.router.getAddress(),
        operations: c.ops.address,
      };
    const validator = await deploy(
      "HoldPresetValidator",
      b.core,
      b.quoteAsset,
      b.router,
      b.rewardsImplementation,
      b.treasuryImplementation,
      6001,
    );
    const p = M.launchParams(ethers, c.selected, b);
    await validator.validate(6001, p);
    await expect(validator.validate(6002, p)).revertedWith("HOLD: preset");
    await expect(
      validator.validate(6001, { ...p, quoteAsset: c.alice.address }),
    ).revertedWith("HOLD: quote");
    await expect(
      validator.validate(6001, { ...p, saleAmount: p.maxSupply }),
    ).revertedWith("HOLD: positive LP reserve");
    await expect(
      validator.validate(6001, { ...p, raiseAmount: 1 }),
    ).revertedWith("HOLD: raise target");
    await expect(
      validator.validate(6001, {
        ...p,
        tokenParams: M.encodeToken(ethers, c.selected, {
          ...b,
          core: c.alice.address,
        }),
      }),
    ).revertedWith("HOLD: trusted components");
  });
  it("retains age taxation and treasury processing through real PancakeSwap graduation", async () => {
    const c = await loadFixture(graduated);
    await dexBuy(c, c.carol, "0.1");
    expect(
      await c.token.exitFeeBps(
        c.carol.address,
        await c.token.balanceOf(c.carol.address),
      ),
    ).eq(1000);
    await dexSell(c, c.carol, (await c.token.balanceOf(c.carol.address)) / 2n);
    expect(await c.token.balanceOf(await c.treasury.getAddress())).greaterThan(
      0,
    );
    await oracle(c);
    const tokens = await c.token.balanceOf(await c.treasury.getAddress());
    // Conversions run separately from sells and retain the treasury oracle guard.
    await c.treasury.convertTax(tokens, (await time.latest()) + 60);
    expect(await c.treasury.received()).greaterThan(0);
  });
});
