const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");
const E = ethers.parseEther,
  DAY = 86400,
  MAX = ethers.MaxUint256;
const WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
  ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E",
  DEAD = "0x000000000000000000000000000000000000dEaD";
async function deploy(name, ...args) {
  const c = await (await ethers.getContractFactory(name)).deploy(...args);
  await c.waitForDeployment();
  return c;
}
function createFixtures(variant) {
  const gas = {};
  async function base(options = {}) {
    if (!process.env.PI_FORK_URL)
      throw Error(
        "PI_FORK_URL is required. These tests use real WBNB and PancakeSwap on a local fork.",
      );
    const [owner, alice, bob, carol, ops] = await ethers.getSigners();
    const quote = await ethers.getContractAt("IWrappedBNB", WBNB),
      router = await ethers.getContractAt("IV2Router", ROUTER);
    const core = await deploy("CoreHarness", WBNB),
      rewardsImpl = await deploy(`${variant}Rewards`),
      treasuryImpl = await deploy(`${variant}Treasury`);
    const implementations = [];
    for (const n of [
      `${variant}Token`,
      `${variant}Vault`,
      `${variant}CurveModule`,
      `${variant}TradeModule`,
      `${variant}MigrateModule`,
    ])
      implementations.push(await deploy(n));
    implementations.push(
      await deploy(`${variant}TokenModule`, await core.getAddress()),
    );
    const abi = ethers.AbiCoder.defaultAbiCoder();
    const model = require("../../../website/protocol-model.js");
    const settings = { ...model.DEFAULTS, ...options };
    const selected = model.exportConfig(settings);
    const bindings = {
      core: await core.getAddress(),
      rewardsImplementation: await rewardsImpl.getAddress(),
      treasuryImplementation: await treasuryImpl.getAddress(),
      router: ROUTER,
      operations: ops.address,
    };
    const config =
      variant === "Pi"
        ? abi.encode(
            [
              "tuple(address core,address rewardsImplementation,address treasuryImplementation,address router,address operations)",
            ],
            [
              [
                bindings.core,
                bindings.rewardsImplementation,
                bindings.treasuryImplementation,
                bindings.router,
                bindings.operations,
              ],
            ],
          )
        : model.encodeToken(ethers, selected, bindings);
    const create = {
      requestId: 1,
      name: settings.name,
      symbol: settings.symbol,
      maxSupply: BigInt(selected.token.maxSupply),
      saleAmount: BigInt(selected.token.saleAmount),
      raiseAmount: BigInt(selected.token.raiseAmount),
      quoteAsset: WBNB,
      tokenUri: "ipfs://review-configuration",
      tokenParams: config,
      tokenSalt: ethers.ZeroHash,
    };
    const curveParams = abi.encode(
      ["tuple(uint256 virtualToken,uint256 virtualQuote)"],
      [
        [
          BigInt(selected.token.virtualToken),
          BigInt(selected.token.virtualQuote),
        ],
      ],
    );
    await core.launch(
      await Promise.all(implementations.map((c) => c.getAddress())),
      create,
      curveParams,
    );
    const token = await ethers.getContractAt(
      `${variant}Token`,
      await core.lastToken(),
    );
    const rewards = await ethers.getContractAt(
        `${variant}Rewards`,
        await token.rewards(),
      ),
      treasury = await ethers.getContractAt(
        `${variant}Treasury`,
        await token.treasury(),
      );
    const vault = await ethers.getContractAt(
        `${variant}Vault`,
        await token.vault(),
      ),
      curve = await ethers.getContractAt(
        `${variant}CurveModule`,
        await token.curveModule(),
      ),
      pair = await ethers.getContractAt("IV2Pair", await token.canonicalPool());
    for (const u of [owner, alice, bob, carol]) {
      await quote.connect(u).deposit({ value: E("1000") });
      await quote.connect(u).approve(await core.getAddress(), MAX);
      await quote.connect(u).approve(ROUTER, MAX);
      await token.connect(u).approve(await core.getAddress(), MAX);
      await token.connect(u).approve(ROUTER, MAX);
    }
    return {
      owner,
      alice,
      bob,
      carol,
      ops,
      quote,
      router,
      core,
      token,
      rewards,
      treasury,
      vault,
      curve,
      pair,
      create,
      curveParams,
      config,
      settings,
      selected,
      rewardsImpl,
      treasuryImpl,
      implementations,
    };
  }
  async function buy(c, u, amount) {
    return c.core.connect(u).buy(await c.token.getAddress(), E(amount));
  }
  async function fund(c, value = "1") {
    await c.quote.transfer(await c.treasury.getAddress(), E(value));
    await c.treasury.sync();
    const a = await c.treasury.available(0);
    await c.treasury.fundHolders(a);
    return a;
  }
  async function graduated() {
    const c = await base();
    await buy(c, c.alice, "1000000");
    await buy(c, c.bob, "799000000");
    const r = await (await c.core.migrate(await c.token.getAddress())).wait();
    gas.migration = r.gasUsed.toString();
    return c;
  }
  async function oracle(c) {
    await c.treasury.observe();
    await time.increase(1801);
    await c.treasury.observe();
  }
  async function dexBuy(c, u, bnb = "0.01") {
    return c.router
      .connect(u)
      .swapExactTokensForTokensSupportingFeeOnTransferTokens(
        E(bnb),
        1,
        [WBNB, await c.token.getAddress()],
        u.address,
        (await time.latest()) + 300,
      );
  }
  async function dexSell(c, u, pi) {
    return c.router
      .connect(u)
      .swapExactTokensForTokensSupportingFeeOnTransferTokens(
        pi,
        1,
        [await c.token.getAddress(), WBNB],
        u.address,
        (await time.latest()) + 300,
      );
  }
  return {
    E,
    DAY,
    MAX,
    WBNB,
    ROUTER,
    DEAD,
    gas,
    deploy,
    base,
    buy,
    fund,
    graduated,
    oracle,
    dexBuy,
    dexSell,
  };
}

module.exports = { createFixtures };
