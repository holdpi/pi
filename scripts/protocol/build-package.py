"""Package the reviewed protocol source with reproducible compiler input."""

from pathlib import Path
import json, hashlib, subprocess, sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_build import load_build, load_verification, write_archive

root = Path(__file__).resolve().parents[2]
out = root / "website/review/protocol"
out.mkdir(parents=True, exist_ok=True)
build = load_build(root)
verification = load_verification(root)
files = {}
for folder, pattern in [
    ("contracts/src", "*.sol"),
    ("contracts/vendor", "*.sol"),
    ("contracts/test", "*.cjs"),
    ("contracts/protocol", "*.cjs"),
]:
    for p in (root / folder).rglob(pattern):
        if p.is_file() and not p.is_symlink():
            files[str(p.relative_to(root))] = p.read_bytes()
for name in [
    "scripts/run-fork-tests.mjs",
    "contracts/test/abi-baseline.json",
    "contracts/protocol/README.md",
    "contracts/protocol/bindings.example.json",
    "contracts/hardhat.config.cjs",
    "contracts/package.json",
    "contracts/package-lock.json",
    "website/protocol-model.js",
    "website/economics.js",
    "tests/economics.test.cjs",
    "contracts/vendor/PROVENANCE.json",
    ".prettierrc.json",
    "tests/protocol-model.test.cjs",
    "website/protocol-zip.js",
]:
    files[name] = (root / name).read_bytes()
files["README.md"] = (root / "contracts/protocol/README.md").read_bytes()
config = json.loads(
    subprocess.check_output(
        [
            "node",
            "-e",
            'const m=require("./website/protocol-model.js");process.stdout.write(JSON.stringify(m.exportConfig(m.DEFAULTS)))',
        ],
        cwd=root,
    )
)
files["configuration.example.json"] = (json.dumps(config, indent=2) + "\n").encode()
compiler = build["input"]
files["compiler-input.json"] = (json.dumps(compiler, indent=2) + "\n").encode()
contracts = []
for p in sorted((root / "contracts/artifacts/src").rglob("*.json")):
    if p.name.endswith(".dbg.json"):
        continue
    a = json.loads(p.read_text())
    name = a["contractName"]
    files[str(p.relative_to(root))] = p.read_bytes()
    if name.startswith("Hold"):
        runtime = len(a["deployedBytecode"][2:]) // 2
        if runtime > 24576:
            raise SystemExit("Runtime too large: " + name)
        contracts.append(
            {"name": name, "runtime_bytes": runtime, "source": a["sourceName"], "abi": a["abi"]}
        )
files["verification.json"] = (json.dumps(verification, indent=2) + "\n").encode()
manifest = {
    "version": "1.1.0-review",
    "status": "Review source. Unregistered. No public-chain deployment.",
    "upstream_commit": "8ca5554df22ad511126d8547c212fa161ecf19ee",
    "compiler": build["solcLongVersion"],
    "contracts": contracts,
    "files": [
        {"path": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
        for n, b in sorted(files.items())
    ],
}
files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
archive = root / "website/review/holdpi-protocol-review.zip"
write_archive(archive, files)
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(out / "README.md").write_bytes(files["README.md"])
(out / "verification.json").write_bytes(files["verification.json"])
receipt = {
    "file": archive.name,
    "bytes": archive.stat().st_size,
    "members": len(files),
    "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
}
(out / "download.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
