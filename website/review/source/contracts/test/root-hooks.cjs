const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function sourceHashes(root) {
  const hashes = {};
  function visit(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const file = path.join(directory, entry.name);
      if (entry.isDirectory()) visit(file);
      else if (/\.(sol|cjs|json)$/.test(entry.name)) {
        hashes[path.relative(root, file).split(path.sep).join("/")] = crypto
          .createHash("sha256")
          .update(fs.readFileSync(file))
          .digest("hex");
      }
    }
  }
  for (const directory of [
    "contracts/src",
    "contracts/vendor",
    "contracts/test",
  ]) {
    visit(path.join(root, directory));
  }
  for (const name of [
    "contracts/hardhat.config.cjs",
    "contracts/package-lock.json",
    "contracts/package.json",
    "scripts/run-fork-tests.mjs",
    "website/economics.js",
    "website/protocol-model.js",
  ]) {
    hashes[name] = crypto
      .createHash("sha256")
      .update(fs.readFileSync(path.join(root, name)))
      .digest("hex");
  }
  return hashes;
}

exports.mochaHooks = {
  async afterAll() {
    const { network } = require("hardhat");
    const root = path.resolve(__dirname, "../..");
    const tests = [];
    function collect(suite) {
      for (const test of suite.tests) {
        tests.push({
          title: test.fullTitle(),
          status: test.state || "pending",
        });
      }
      suite.suites.forEach(collect);
    }
    collect(this.test.parent);
    const metadata = await network.provider.send("hardhat_metadata");
    const report = {
      scope:
        "WBNB and PancakeSwap V2 on a local BNB fork with CoreHarness settlement.",
      checkedAt: new Date().toISOString(),
      compiler: require("solc").version(),
      fork: metadata.forkedNetwork || null,
      sourceHashes: sourceHashes(root),
      gasUnits: {
        fixed: require("./fixtures.cjs").gas,
        configurable: require("./protocol-fixtures.cjs").gas,
      },
      tests,
    };
    const filename = metadata.forkedNetwork
      ? "contract-verification.json"
      : "unit-verification.json";
    const directory = path.join(root, "outputs");
    fs.mkdirSync(directory, { recursive: true });
    fs.writeFileSync(
      path.join(directory, filename),
      JSON.stringify(report, null, 2) + "\n",
    );
  },
};
