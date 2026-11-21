/* Read-only preparation and simulation. Never sends a transaction or reads a key. */
const fs = require("node:fs");
const path = require("node:path");
const ethers = require("ethers");
const M = require("../../website/protocol-model.js");
const PARAM =
  "tuple(string name,string abiType,uint8 decimals,bool optional,string title,string defaultValue,string hint,string minValue,string maxValue)";
const SCHEMA = `tuple(string kind,uint8 version,${PARAM}[] params)`;
const PRESET =
  "tuple(uint256 id,string name,string description,string version,bool active,bool createEnabled,address validator,bytes32 tokenModuleId,bytes32 vaultModuleId,bytes32 curveModuleId,bytes32 tradeModuleId,bytes32 migrateModuleId,bytes32 tokenImplId,bytes32 customDataId,address author)";
const CORE_ABI = [
  "function createToken(bytes createArgs,bytes signature) payable returns(address)",
  "function registry() view returns(address)",
  "function wrappedNative() view returns(address)",
  "function signer() view returns(address)",
];
async function prepare(config, bindings, rpc) {
  const settings = M.importConfig(config),
    canonical = M.exportConfig(settings);
  if (
    JSON.stringify(config.policy) !== JSON.stringify(canonical.policy) ||
    JSON.stringify(config.token) !== JSON.stringify(canonical.token)
  )
    throw Error(
      "Configuration differs from its settings. Re-export it in the builder.",
    );
  const provider = new ethers.JsonRpcProvider(rpc),
    network = await provider.getNetwork();
  if (network.chainId !== BigInt(bindings.chainId)) throw Error("Wrong chain.");
  if (
    !ethers.isAddress(bindings.caller) ||
    bindings.caller === ethers.ZeroAddress
  )
    throw Error("Caller address is required.");
  for (const k of [
    "core",
    "rewardsImplementation",
    "treasuryImplementation",
    "router",
  ])
    if ((await provider.getCode(bindings[k])) === "0x")
      throw Error("Missing deployed code: " + k);
  const core = new ethers.Contract(bindings.core, CORE_ABI, provider),
    registryAddress = await core.registry();
  if (registryAddress.toLowerCase() !== String(bindings.registry).toLowerCase())
    throw Error("Registry mismatch.");
  const registry = new ethers.Contract(
    registryAddress,
    [
      `function getPreset(uint256) view returns(${PRESET})`,
      "function openFourTool() view returns(address)",
      "function getTokenImpl(bytes32) view returns(tuple(address implementation,string version))",
      "function getModuleImplementation(bytes32) view returns(address)",
    ],
    provider,
  );
  const preset = await registry.getPreset(bindings.presetId);
  if (!preset.active || !preset.createEnabled)
    throw Error("Preset is not enabled for creation.");
  if (preset.validator === ethers.ZeroAddress)
    throw Error("An approved validator is required.");
  // Compare every registered implementation against the reviewed deployment manifest.
  if (!bindings.implementations)
    throw Error("A reviewed implementations manifest is required.");
  const tokenImpl = await registry.getTokenImpl(preset.tokenImplId);
  if (
    tokenImpl.implementation.toLowerCase() !==
    bindings.implementations.token.toLowerCase()
  )
    throw Error("Token implementation mismatch.");
  for (const slot of ["tokenModule", "vault", "curve", "trade", "migrate"]) {
    const key =
      preset[slot === "tokenModule" ? "tokenModuleId" : slot + "ModuleId"];
    const actual = await registry.getModuleImplementation(key);
    if (actual.toLowerCase() !== bindings.implementations[slot].toLowerCase())
      throw Error("Module implementation mismatch: " + slot);
  }
  const tools = new ethers.Contract(
    await registry.openFourTool(),
    [
      `function getTokenBaseSchema() view returns(${PARAM}[])`,
      `function getPresetEncodeSchemas(uint256) view returns(${SCHEMA},${SCHEMA},${SCHEMA},${SCHEMA},${SCHEMA},${SCHEMA})`,
    ],
    provider,
  );
  await tools.getTokenBaseSchema();
  const schemas = await tools.getPresetEncodeSchemas(bindings.presetId);
  const type =
    "tuple(" +
    schemas[0].params.map((p) => p.abiType + " " + p.name).join(",") +
    ")";
  if (type !== M.TOKEN_TYPE)
    throw Error("On-chain token schema does not match this builder version.");
  if (
    schemas[2].params.map((p) => p.abiType + " " + p.name).join(",") !==
    "uint256 virtualToken,uint256 virtualQuote"
  )
    throw Error("Curve schema mismatch.");
  for (const i of [1, 3, 4, 5])
    if (schemas[i].params.length) throw Error("Unexpected module parameters.");
  const wrapped = await core.wrappedNative();
  if (wrapped.toLowerCase() !== bindings.quoteAsset.toLowerCase())
    throw Error("This protocol requires Core wrapped native BNB.");
  const init = M.launchParams(ethers, config, bindings);
  await new ethers.Contract(
    preset.validator,
    [`function validate(uint256,${M.INIT_TYPE}) view`],
    provider,
  ).validate(bindings.presetId, init);
  const current = await provider.getBlock("latest"),
    validTimestamp = Number(
      bindings.validTimestamp || current.timestamp + 3600,
    );
  if (validTimestamp <= current.timestamp)
    throw Error("Creation request is expired.");
  if (!bindings.requestId) throw Error("Provide an unused requestId.");
  const request = {
    requestId: bindings.requestId,
    presetId: bindings.presetId,
    validTimestamp,
    createFee: bindings.createFee || "0",
    presaleQuote: "0",
    antiSniperEnabled: false,
    partner: ethers.ZeroAddress,
    initParams: init,
  };
  const createArgs = ethers.AbiCoder.defaultAbiCoder().encode(
    [M.CREATE_TYPE],
    [request],
  );
  const digest = ethers.keccak256(
    ethers.solidityPacked(
      ["string", "uint256", "address", "bytes32"],
      [
        "createOpenFourToken",
        network.chainId,
        bindings.caller,
        ethers.keccak256(createArgs),
      ],
    ),
  );
  const authorizedSigner = await core.signer();
  const output = {
    chainId: network.chainId.toString(),
    core: bindings.core,
    caller: bindings.caller,
    requestId: String(request.requestId),
    presetId: String(request.presetId),
    validTimestamp,
    value: String(request.createFee),
    createArgs,
    signMessageBytes: digest,
    authorizedSigner,
    simulation: "signature-required",
  };
  if (bindings.signature) {
    if (
      ethers
        .verifyMessage(ethers.getBytes(digest), bindings.signature)
        .toLowerCase() !== authorizedSigner.toLowerCase()
    )
      throw Error("Signature is not from Core.signer().");
    const predicted = await core.createToken.staticCall(
      createArgs,
      bindings.signature,
      { from: bindings.caller, value: request.createFee },
    );
    output.simulation = "passed";
    output.predictedToken = predicted;
    output.transaction = {
      to: bindings.core,
      from: bindings.caller,
      value: String(request.createFee),
      data: core.interface.encodeFunctionData("createToken", [
        createArgs,
        bindings.signature,
      ]),
    };
  }
  return output;
}
if (require.main === module) {
  const [configFile, bindingsFile, outputFile] = process.argv.slice(2);
  if (!configFile || !bindingsFile || !outputFile || !process.env.RPC_URL) {
    console.error(
      "RPC_URL=... node contracts/protocol/prepare-create.cjs configuration.json bindings.json prepared-create.json",
    );
    process.exitCode = 1;
  } else
    prepare(
      JSON.parse(fs.readFileSync(configFile)),
      JSON.parse(fs.readFileSync(bindingsFile)),
      process.env.RPC_URL,
    )
      .then((result) => {
        fs.writeFileSync(outputFile, JSON.stringify(result, null, 2) + "\n");
        console.log(
          "Prepared " +
            path.basename(outputFile) +
            ". Simulation: " +
            result.simulation +
            ". No transaction was sent.",
        );
      })
      .catch((e) => {
        console.error(e.shortMessage || e.message);
        process.exitCode = 1;
      });
}
module.exports = { prepare, CORE_ABI };
