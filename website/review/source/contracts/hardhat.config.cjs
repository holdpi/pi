const path = require("node:path");
require("@nomicfoundation/hardhat-ethers");
require("@nomicfoundation/hardhat-chai-matchers");
const { subtask } = require("hardhat/config");
const {
  TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD,
} = require("hardhat/builtin-tasks/task-names");
subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD).setAction(
  async ({ solcVersion }) => ({
    compilerPath: require.resolve("solc/soljson.js"),
    isSolcJs: true,
    version: solcVersion,
    longVersion: require("solc").version(),
  }),
);
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      viaIR: true,
      evmVersion: "paris",
    },
  },
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {
      chainId: 31337,
      ...(process.env.PI_FORK_URL
        ? {
            forking: {
              url: process.env.PI_FORK_URL,
              ...(process.env.PI_FORK_BLOCK
                ? { blockNumber: Number(process.env.PI_FORK_BLOCK) }
                : {}),
            },
          }
        : {}),
    },
  },
  paths: {
    sources: path.join(__dirname, "src"),
    tests: path.join(__dirname, "test"),
    cache: path.join(__dirname, "cache"),
    artifacts: path.join(__dirname, "artifacts"),
  },
  mocha: {
    timeout: 120000,
    rootHooks: require("./test/root-hooks.cjs").mochaHooks,
  },
};
