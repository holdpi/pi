(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldProtocol = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const VERSION = "holdpi.protocol.v1";
  const DEFAULTS = Object.freeze({
    buy: 5,
    sellStart: 10,
    sellFloor: 1,
    decayDays: 30,
    curve: "pi",
    roundMinutes: 15,
    qualificationDays: 1,
    loyaltyDays: 30,
    maxWeight: 2,
    rewardCurve: "pi",
    minFunding: "0",
    holders: 70,
    burn: 15,
    liquidity: 10,
    operations: 5,
    name: "Passive Income",
    symbol: "PI",
    supply: "1000000000",
    raiseBNB: "400",
    volume: 100,
    buyShare: 50,
    sellAge: 7,
    conversionCost: 0.5,
    holdingDays: 7,
    holding: 1000000,
    otherWeight: 500000000,
  });
  const TOKEN_TYPE =
    "tuple(address core,address rewardsImplementation,address treasuryImplementation,address router,address operations,uint16 buyBps,uint16[] sellBps,uint16[] weightBps,uint32 roundSeconds,uint256 minFunding,uint16[] splitBps)";
  const INIT_TYPE =
    "tuple(string name,string symbol,string tokenUri,uint256 maxSupply,uint256 saleAmount,uint256 raiseAmount,address quoteAsset,bytes32 tokenSalt,bytes tokenParams,bytes vaultParams,bytes curveParams,bytes tradeParams,bytes migrateParams,bytes customDataParams)";
  const CREATE_TYPE =
    "tuple(uint256 requestId,uint256 presetId,uint256 validTimestamp,uint256 createFee,uint256 presaleQuote,bool antiSniperEnabled,address partner," +
    INIT_TYPE +
    " initParams)";
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  function validate(settings) {
    const errors = [];
    function num(k, lo, hi, integer = false) {
      if (
        typeof settings[k] !== "number" ||
        !Number.isFinite(settings[k]) ||
        settings[k] < lo ||
        settings[k] > hi ||
        (integer && !Number.isInteger(settings[k]))
      )
        errors.push(k + " is outside its supported range.");
    }
    ["buy", "sellStart", "sellFloor"].forEach((k) => num(k, 0, 10));
    if (settings.sellFloor > settings.sellStart)
      errors.push("The sell floor must be at or below the starting tax.");
    num("decayDays", 1, 30, true);
    num("roundMinutes", 1, 1440, true);
    num("qualificationDays", 1, 30, true);
    num("loyaltyDays", 1, 30, true);
    num("maxWeight", 1, 5);
    if (settings.loyaltyDays < settings.qualificationDays)
      errors.push("Maximum loyalty must come after qualification.");
    if (!["pi", "linear", "early", "late"].includes(settings.curve))
      errors.push("Choose a supported sell curve.");
    if (!["pi", "linear"].includes(settings.rewardCurve))
      errors.push("Choose a supported reward curve.");
    ["holders", "burn", "liquidity", "operations"].forEach((k) =>
      num(k, 0, 100, true),
    );
    if (
      settings.holders +
        settings.burn +
        settings.liquidity +
        settings.operations !==
      100
    )
      errors.push("Treasury allocations must add up to 100%.");
    num("volume", 0, 1e9);
    num("buyShare", 0, 100);
    num("sellAge", 0, 30, true);
    num("conversionCost", 0, 100);
    num("holdingDays", 0, 30, true);
    num("holding", 0, 1e18);
    num("otherWeight", 0, 1e20);
    try {
      const n = wei(settings.minFunding);
      if (n < 0n || n > 10n ** 24n) throw 0;
    } catch {
      errors.push(
        "Minimum funding must be a BNB amount between 0 and 1,000,000.",
      );
    }
    if (
      typeof settings.name !== "string" ||
      !settings.name.trim() ||
      new TextEncoder().encode(settings.name).length > 64
    )
      errors.push("Use a token name of 1 to 64 UTF-8 bytes.");
    if (
      typeof settings.symbol !== "string" ||
      !/^[A-Za-z0-9]{1,12}$/.test(settings.symbol)
    )
      errors.push("Use a ticker of 1 to 12 letters or numbers.");
    if (
      typeof settings.supply !== "string" ||
      !/^\d+$/.test(settings.supply) ||
      BigInt(settings.supply) < 5n ||
      BigInt(settings.supply) > 10n ** 12n
    )
      errors.push("Supply must be a whole number from 5 to 1 trillion tokens.");
    try {
      const n = wei(settings.raiseBNB);
      if (n <= 0n || n > 10n ** 24n || n % 4n) throw 0;
    } catch {
      errors.push(
        "Use a positive BNB raise target with at most 15 decimal places.",
      );
    }
    return errors;
  }
  function wei(value) {
    const decimal = String(value);
    if (!/^\d+(\.\d{1,18})?$/.test(decimal)) throw Error("Invalid decimal");
    const [a, b = ""] = decimal.split(".");
    return BigInt(a) * 10n ** 18n + BigInt(b.padEnd(18, "0"));
  }
  function interpolate(x, knots) {
    if (x <= knots[0][0]) return knots[0][1];
    for (let i = 1; i < knots.length; i++)
      if (x <= knots[i][0]) {
        const [a, h] = knots[i - 1],
          [b, l] = knots[i];
        return h + ((l - h) * (x - a)) / (b - a);
      }
    return knots.at(-1)[1];
  }
  function sellTable(settings) {
    const start = Math.round(settings.sellStart * 100),
      floor = Math.round(settings.sellFloor * 100);
    return Array.from({ length: 31 }, (_, d) => {
      const x = clamp(d / settings.decayDays, 0, 1);
      const progress =
        settings.curve === "pi"
          ? 1 -
            interpolate(x * 30, [
              [0, 1],
              [1, 7 / 9],
              [3, 5 / 9],
              [7, 3 / 9],
              [14, 1 / 9],
              [30, 0],
            ])
          : settings.curve === "early"
            ? 1 - (1 - x) ** 3
            : settings.curve === "late"
              ? x ** 3
              : x;
      // Round the reduction down, including a small float tolerance at exact bps.
      return clamp(
        start - Math.floor((start - floor) * progress + 1e-9),
        floor,
        start,
      );
    });
  }
  function weightTable(settings) {
    return Array.from({ length: 31 }, (_, d) => {
      if (d < settings.qualificationDays) return 0;
      const x =
        settings.loyaltyDays === settings.qualificationDays
          ? 1
          : clamp(
              (d - settings.qualificationDays) /
                (settings.loyaltyDays - settings.qualificationDays),
              0,
              1,
            );
      const progress =
        settings.rewardCurve === "pi"
          ? x >= 1
            ? 1
            : x >= 6 / 29
              ? 0.5
              : 0
          : x;
      return Math.round((1 + (settings.maxWeight - 1) * progress) * 10000);
    });
  }
  function policy(settings) {
    const errors = validate(settings);
    if (errors.length) throw Error(errors.join(" "));
    return {
      buyBps: Math.round(settings.buy * 100),
      sellBps: sellTable(settings),
      weightBps: weightTable(settings),
      roundSeconds: settings.roundMinutes * 60,
      minFunding: wei(settings.minFunding).toString(),
      splitBps: [
        settings.holders,
        settings.burn,
        settings.liquidity,
        settings.operations,
      ].map((x) => x * 100),
    };
  }
  function result(settings) {
    const sells = sellTable(settings),
      weights = weightTable(settings),
      age = clamp(Math.floor(settings.sellAge), 0, 30),
      held = clamp(Math.floor(settings.holdingDays), 0, 30);
    const buyVolume =
      (Math.max(0, settings.volume) * clamp(settings.buyShare, 0, 100)) / 100;
    const sellVolume = Math.max(0, settings.volume) - buyVolume;
    const gross =
      (buyVolume * settings.buy) / 100 + (sellVolume * sells[age]) / 10000;
    const net = gross * (1 - clamp(settings.conversionCost, 0, 100) / 100);
    const split = [
      settings.holders,
      settings.burn,
      settings.liquidity,
      settings.operations,
    ].map((x) => (net * x) / 100);
    const weight = (Math.max(0, settings.holding) * weights[held]) / 10000;
    const share = weight / (Math.max(0, settings.otherWeight) + weight) || 0;
    const roundFund = (split[0] * settings.roundMinutes) / 1440;
    return {
      sellRate: sells[age] / 100,
      weight: weights[held] / 10000,
      gross,
      net,
      split,
      share,
      payout: split[0] * share,
      roundFund,
      roundPayout: roundFund * share,
      canSettle: roundFund > 0 && roundFund >= Number(settings.minFunding),
    };
  }
  function exportConfig(settings) {
    const p = policy(settings),
      supply = BigInt(settings.supply) * 10n ** 18n;
    return {
      schema: VERSION,
      network: "BNB Smart Chain",
      chainId: 56,
      rewardAsset: "BNB",
      protocolStatus: "review-source-unregistered",
      settings: Object.fromEntries(
        Object.keys(DEFAULTS).map((k) => [k, settings[k]]),
      ),
      policy: p,
      token: {
        name: settings.name.trim(),
        symbol: settings.symbol,
        maxSupply: supply.toString(),
        saleAmount: ((supply * 4n) / 5n).toString(),
        raiseAmount: wei(settings.raiseBNB).toString(),
        virtualToken: supply.toString(),
        virtualQuote: (wei(settings.raiseBNB) / 4n).toString(),
      },
      semantics: {
        age: "max(0,floor(now/86400)-ceil(acquisition/86400))",
        exits: "newest-first; transfers taxed and reset recipient age",
        settlement: "permissionless funded rounds; user claims BNB or WBNB",
        policy:
          "fixed per token initialization; OpenFour upgrade authority remains external",
      },
    };
  }
  function importConfig(input) {
    if (input?.schema !== VERSION || !input.settings)
      throw Error("This is not a HoldPI protocol configuration.");
    const settings = { ...DEFAULTS };
    for (const k of Object.keys(DEFAULTS))
      if (Object.hasOwn(input.settings, k)) settings[k] = input.settings[k];
    const errors = validate(settings);
    if (errors.length) throw Error(errors.join(" "));
    for (const k of [
      "volume",
      "buyShare",
      "sellAge",
      "conversionCost",
      "holdingDays",
      "holding",
      "otherWeight",
    ])
      if (!Number.isFinite(settings[k]) || settings[k] < 0)
        throw Error("Invalid scenario value: " + k);
    return settings;
  }
  function encodeToken(ethers, config, bindings) {
    const p = config.policy;
    for (const k of [
      "core",
      "rewardsImplementation",
      "treasuryImplementation",
      "router",
      "operations",
    ])
      if (!ethers.isAddress(bindings[k]) || bindings[k] === ethers.ZeroAddress)
        throw Error("Missing address: " + k);
    return ethers.AbiCoder.defaultAbiCoder().encode(
      [TOKEN_TYPE],
      [
        [
          bindings.core,
          bindings.rewardsImplementation,
          bindings.treasuryImplementation,
          bindings.router,
          bindings.operations,
          p.buyBps,
          p.sellBps,
          p.weightBps,
          p.roundSeconds,
          p.minFunding,
          p.splitBps,
        ],
      ],
    );
  }
  function launchParams(ethers, config, bindings) {
    const t = config.token;
    return {
      name: t.name,
      symbol: t.symbol,
      tokenUri: bindings.tokenUri || "",
      maxSupply: t.maxSupply,
      saleAmount: t.saleAmount,
      raiseAmount: t.raiseAmount,
      quoteAsset: bindings.quoteAsset,
      tokenSalt: bindings.tokenSalt || ethers.ZeroHash,
      tokenParams: encodeToken(ethers, config, bindings),
      vaultParams: "0x",
      curveParams: ethers.AbiCoder.defaultAbiCoder().encode(
        ["tuple(uint256 virtualToken,uint256 virtualQuote)"],
        [[t.virtualToken, t.virtualQuote]],
      ),
      tradeParams: "0x",
      migrateParams: "0x",
      customDataParams: "0x",
    };
  }
  return {
    VERSION,
    DEFAULTS,
    TOKEN_TYPE,
    INIT_TYPE,
    CREATE_TYPE,
    validate,
    wei,
    sellTable,
    weightTable,
    policy,
    result,
    exportConfig,
    importConfig,
    encodeToken,
    launchParams,
  };
});
