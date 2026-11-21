import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const contracts = fileURLToPath(new URL("../contracts", import.meta.url));
const rpcUrl = process.env.PI_FORK_URL || "https://bsc-rpc.publicnode.com";

async function rpc(method, params = []) {
  const response = await fetch(rpcUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) throw new Error(`BNB RPC returned HTTP ${response.status}`);
  const payload = await response.json();
  if (payload.error)
    throw new Error(`BNB RPC rejected ${method}: ${payload.error.message}`);
  return payload.result;
}

try {
  if (Number(await rpc("eth_chainId")) !== 56) {
    throw new Error(
      "The contract suite requires a BNB Smart Chain RPC (chain ID 56).",
    );
  }
  const blockNumber = process.env.PI_FORK_BLOCK
    ? Number(process.env.PI_FORK_BLOCK)
    : Number(await rpc("eth_blockNumber")) - 64;
  if (!Number.isSafeInteger(blockNumber) || blockNumber <= 0) {
    throw new Error("PI_FORK_BLOCK must be a positive safe integer.");
  }
  const block = await rpc("eth_getBlockByNumber", [
    `0x${blockNumber.toString(16)}`,
    false,
  ]);
  if (!block?.hash)
    throw new Error("The RPC could not serve the selected fork block.");
  console.log(`BNB fork block ${blockNumber}, hash ${block.hash}`);
  const result = spawnSync(
    process.execPath,
    [
      "node_modules/hardhat/internal/cli/cli.js",
      "test",
      ...process.argv.slice(2),
    ],
    {
      cwd: contracts,
      stdio: "inherit",
      env: {
        ...process.env,
        PI_FORK_URL: rpcUrl,
        PI_FORK_BLOCK: String(blockNumber),
      },
    },
  );
  if (result.error) throw result.error;
  process.exitCode = result.status ?? 1;
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
