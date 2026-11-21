// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {HoldConfig} from "./HoldConfig.sol";
import {Clones} from "@openzeppelin/contracts/proxy/Clones.sol";
import {AcquisitionToken} from "../common/AcquisitionToken.sol";
import {HoldRewards} from "./HoldRewards.sol";
import {HoldTreasury} from "./HoldTreasury.sol";

/// @notice Configurable OpenFour token. Policy is fixed during each initialization.
/// @dev Registry-controlled beacon upgrades are an external trust boundary.
contract HoldToken is AcquisitionToken {
    uint256 public buyFeeRate;
    uint256 public sellFeeRate;
    bytes32 public policyHash;

    function initialize(InitArgs calldata c) external override initializer {
        require(msg.sender == c.tokenModule, "HOLD: token module only");
        require(
            c.maxSupply > 0 &&
                c.maxSupply <= 1e30 &&
                c.quoteAsset.code.length > 0,
            "HOLD: supply or quote"
        );
        HoldConfig.Config memory p = abi.decode(
            c.tokenParams,
            (HoldConfig.Config)
        );
        HoldConfig.validate(p);
        buyFeeRate = p.buyBps;
        sellFeeRate = p.sellBps[0];
        policyHash = keccak256(c.tokenParams);
        require(
            p.core.code.length > 0 &&
                p.rewardsImplementation.code.length > 0 &&
                p.treasuryImplementation.code.length > 0,
            "HOLD: implementations"
        );
        core = p.core;
        rewards = HoldRewards(payable(Clones.clone(p.rewardsImplementation)));
        treasury = HoldTreasury(Clones.clone(p.treasuryImplementation));
        HoldRewards(payable(address(rewards))).initialize(
            address(this),
            c.quoteAsset,
            address(treasury),
            p.sellBps,
            p.weightBps,
            p.roundSeconds,
            p.minFunding
        );
        HoldTreasury(address(treasury)).initialize(
            address(this),
            c.quoteAsset,
            address(rewards),
            p.operations,
            p.router,
            p.splitBps
        );
        _registerPool(p.router, c.quoteAsset);
        __OpenFourToken_init(c);
    }
    function _descriptorTag() internal pure override returns (string memory) {
        return "token.holdpi_configurable";
    }
    function _buyBps() internal view override returns (uint256) {
        return buyFeeRate;
    }
    function _error(
        string memory reason
    ) internal pure override returns (string memory) {
        return string.concat("HOLD: ", reason);
    }
}
