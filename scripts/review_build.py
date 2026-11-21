"""Build validation and deterministic archive writing shared by both review exports."""

import hashlib
import json
import os
from pathlib import PurePosixPath
import zipfile


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_build(root):
    """Require one complete compiler input matching every editable Solidity source."""
    contracts = root / "contracts"
    expected = {
        str(path.relative_to(contracts)): path.read_text()
        for folder in ["src", "vendor"]
        for path in (contracts / folder).rglob("*.sol")
    }
    candidates = sorted((contracts / "artifacts/build-info").glob("*.json"))
    for path in candidates:
        build = json.loads(path.read_text())
        sources = build["input"]["sources"]
        if all(
            sources.get(name, {}).get("content") == content for name, content in expected.items()
        ):
            return build
    raise SystemExit("Run npm run compile:clean before packaging changed contracts.")


def load_verification(root):
    """Reject failed runs and receipts that belong to different source or tests."""
    report = json.loads((root / "outputs/contract-verification.json").read_text())
    if not report.get("fork") or not report.get("tests"):
        raise SystemExit("Run the full BNB fork suite before packaging.")
    if any(test["status"] != "passed" for test in report["tests"]):
        raise SystemExit("The contract verification receipt contains unsuccessful tests.")
    required_suites = [
        "Fixed PI contracts on a BNB fork",
        "Configurable contracts with PI defaults on a BNB fork",
        "HoldPI configurable protocol",
        "Public ABI compatibility with the initial audit snapshot",
    ]
    for suite in required_suites:
        if not any(test["title"].startswith(suite + " ") for test in report["tests"]):
            raise SystemExit("The full contract suite must include " + suite)
    hashes = report.get("sourceHashes", {})
    required = {
        str(path.relative_to(root))
        for folder in ["contracts/src", "contracts/vendor", "contracts/test"]
        for path in (root / folder).rglob("*")
        if path.suffix in {".sol", ".cjs", ".json"}
    }
    required.update(
        [
            "contracts/hardhat.config.cjs",
            "contracts/package-lock.json",
            "contracts/package.json",
            "scripts/run-fork-tests.mjs",
            "website/economics.js",
            "website/protocol-model.js",
        ]
    )
    if set(hashes) != required:
        raise SystemExit(
            "The contract receipt does not cover the complete current source and tests."
        )
    for name, expected in hashes.items():
        if sha256((root / name).read_bytes()) != expected:
            raise SystemExit("Rerun the contract tests after changing " + name)
    return report


def write_archive(path, files):
    """Normalize order, timestamps and permissions, then atomically replace the ZIP."""
    temporary = path.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, content in sorted(files.items()):
                member = PurePosixPath(name)
                forbidden = {".git", "node_modules", ".venv", "__pycache__"}
                local_bindings = {
                    "bindings.json",
                    "fork-bindings.json",
                    "local-deployment.json",
                    "prepared-create.json",
                }
                if (
                    member.is_absolute()
                    or ".." in member.parts
                    or "\\" in name
                    or forbidden.intersection(member.parts)
                    or member.name.startswith(".env")
                    or member.name in local_bindings
                    or member.suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
                ):
                    raise ValueError("Private or unsafe review member: " + name)
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, content, compresslevel=9)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("Review archive failed its integrity check")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
