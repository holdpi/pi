// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {IOpenFourPresetValidator} from "../../vendor/openfour/interfaces/IOpenFourPresetValidator.sol";
import {OpenFourTypes} from "../../vendor/openfour/libraries/OpenFourTypes.sol";
import {HoldConfig} from "./HoldConfig.sol";
import {HoldToken} from "./HoldToken.sol";
import {PiCurveModule} from "../PiCurveModule.sol";
import {PiMigrateModule} from "../PiMigrateModule.sol";

/// @notice Deployment-specific bindings must be reviewed with the preset registry.
contract HoldPresetValidator is IOpenFourPresetValidator {
    address public immutable core;
    address public immutable quote;
    address public immutable router;
    address public immutable rewardsImpl;
    address public immutable treasuryImpl;
    uint256 public immutable presetId;
    constructor(
        address core_,
        address quote_,
        address router_,
        address rewards_,
        address treasury_,
        uint256 preset_
    ) {
        require(
            core_ != address(0) &&
                quote_ != address(0) &&
                router_ != address(0) &&
                rewards_ != address(0) &&
                treasury_ != address(0),
            "HOLD: validator binding"
        );
        core = core_;
        quote = quote_;
        router = router_;
        rewardsImpl = rewards_;
        treasuryImpl = treasury_;
        presetId = preset_;
    }
    function validate(
        uint256 id,
        OpenFourTypes.TokenInitParams calldata p
    ) external view {
        require(presetId == 0 || id == presetId, "HOLD: preset");
        require(
            bytes(p.name).length > 0 &&
                bytes(p.name).length <= 64 && bytes(p.symbol).length > 0 && bytes(p.symbol).length <= 12,
            "HOLD: identity"
        );
        require(
            p.maxSupply > 0 && p.maxSupply <= 1e30 &&
                p.saleAmount > 0 &&
                p.saleAmount < p.maxSupply,
            "HOLD: positive LP reserve"
        );
        require(p.quoteAsset == quote, "HOLD: quote");
        require(
            p.vaultParams.length == 0 &&
                p.tradeParams.length == 0 &&
                p.customDataParams.length == 0 &&
                p.migrateParams.length == 0,
            "HOLD: unexpected params"
        );
        HoldConfig.Config memory t = abi.decode(p.tokenParams, (HoldConfig.Config));
        HoldConfig.validate(t);
        require(
            t.core == core &&
                t.router == router &&
                t.rewardsImplementation == rewardsImpl &&
                t.treasuryImplementation == treasuryImpl &&
                t.operations != address(0),
            "HOLD: trusted components"
        );
        PiCurveModule.Config memory c = abi.decode(
            p.curveParams,
            (PiCurveModule.Config)
        );
        require(
            c.virtualToken > p.saleAmount &&
                c.virtualToken <= 1e30 &&
                c.virtualQuote > 0 &&
                c.virtualQuote <= 1e30,
            "HOLD: curve reserves"
        );
        require(
            p.raiseAmount ==
                Math.mulDiv(
                    c.virtualQuote,
                    p.saleAmount,
                    c.virtualToken - p.saleAmount,
                    Math.Rounding.Up
                ),
            "HOLD: raise target"
        );
        uint256 requiredLP = Math.mulDiv(
            p.saleAmount,
            c.virtualToken - p.saleAmount,
            c.virtualToken,
            Math.Rounding.Up
        );
        require(
            requiredLP <= p.maxSupply - p.saleAmount,
            "HOLD: terminal LP inventory"
        );
    }
}
