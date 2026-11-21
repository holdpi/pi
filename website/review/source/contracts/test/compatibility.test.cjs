const { expect } = require("chai");
const { artifacts, ethers } = require("hardhat");
const baseline = require("./abi-baseline.json");

function publicSurface(abi) {
  const contract = new ethers.Interface(abi);
  return contract.fragments
    .filter((fragment) =>
      ["function", "event", "error"].includes(fragment.type),
    )
    .map((fragment) => {
      const signature = `${fragment.type} ${fragment.format("sighash")}`;
      if (fragment.type === "function") {
        return `${signature} ${fragment.stateMutability} -> ${fragment.outputs.map((output) => output.format("sighash")).join(",")}`;
      }
      if (fragment.type === "event") {
        return `${signature} indexed=${fragment.inputs.map((input) => Boolean(input.indexed)).join(",")} anonymous=${fragment.anonymous}`;
      }
      return signature;
    })
    .sort();
}

describe("Public ABI compatibility with the initial audit snapshot", function () {
  for (const [name, abi] of Object.entries(baseline.contracts)) {
    it(`preserves ${name} callable signatures, return types and event indexing`, async function () {
      const current = await artifacts.readArtifact(name);
      expect(publicSurface(current.abi)).to.deep.equal(publicSurface(abi));
    });
  }
});
